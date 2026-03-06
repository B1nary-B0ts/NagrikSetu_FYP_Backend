from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from django.conf import settings

from ai_service_proxy.tasks.issue_pipeline import process_issue_report

from .models import Issue, IssueReport
from .serializers import IssueReportCreateSerializer, IssueSerializer, MyIssueSerializer

from .utils.temp_storage import save_temp_image, delete_temp_image
from .utils.cloudinary import upload_image

class ReportIssueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IssueReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user

        if user.role != "citizen":
            return Response(
                {"error": "Only citizens can report issues"},
                status=status.HTTP_403_FORBIDDEN
            )

        image_file = data["image"]

        with transaction.atomic():

            # issue = Issue.objects.create(
            #     ward_id=data["ward_id"],
            #     municipal_corp_id=data["municipal_corp_id"],
            #     latitude=data["latitude"],
            #     longitude=data["longitude"],
            #     status="PROCESSING",
            # )

            local_image_path = save_temp_image(image_file)
            # upload_result = upload_image(image_file)
            with open(local_image_path, "rb") as f:
                upload_result = upload_image(f)
            image_url = upload_result["secure_url"]

            issue_report = IssueReport.objects.create(
                #issue=issue,
                issue=None,
                citizen=user,
                description=data.get("description"),
                image_url=image_url,
                local_image_path=local_image_path,
            )

        process_issue_report.delay(
            issue_report.id,
            ward_id=data["ward_id"],
            municipal_corp_id=data["municipal_corp_id"],
            latitude=str(data["latitude"]),
            longitude=str(data["longitude"]),
        )

        return Response(
            {
                "message": "Issue reported successfully",
                #"issue": IssueSerializer(issue).data
                "issue_report_id": issue_report.id,
            },
            status=status.HTTP_201_CREATED
        )

class MyIssuesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != "citizen":
            return Response(
                {"error": "Only citizens can view their issues"},
                status=status.HTTP_403_FORBIDDEN
            )

        issues = Issue.objects.filter(
            reports__citizen=user
        ).distinct().select_related("ward", "municipal_corp", "dept")

        serializer = MyIssueSerializer(issues, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)