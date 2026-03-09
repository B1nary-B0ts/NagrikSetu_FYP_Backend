from django.shortcuts import render
from django.db.models import Count, Case, When, IntegerField
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from issues.models import Issue
from .serializers import DeptHeadIssueSerializer
# Create your views here.

class DeptHeadIssuesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != "dept_head":
            return Response(
                {"error": "Unauthorized access. Only department heads can access this"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            dept_head = user.dept_head_profile # fetches the DepartmentHead instance related to the user
        except Exception:
            return Response(
                {"error": "Department head profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        filters = {
            "dept": dept_head.dept,
            "municipal_corp": dept_head.municipal_corp,
        }
        if dept_head.ward:
            filters["ward"] = dept_head.ward

        severity_order = Case(                  # case helps to order the severity levels in a specific way
            When(severity="CRITICAL", then=0),
            When(severity="HIGH",     then=1),
            When(severity="MEDIUM",   then=2),
            When(severity="LOW",      then=3),
            default=4,
            output_field=IntegerField(),
        )

        issues = Issue.objects.filter(
            **filters
        ).exclude(
            status__in=["CLOSED", "REJECTED"]
        ).annotate(
            report_count = Count("reports"), # reports is the related_name for IssueReport in the Issue model and count the number of reports for each issue
        ).order_by(
            severity_order,
            "-report_count",
            "-created_at"
        ).select_related(
            "ward", "municipal_corp", "dept"
        )

        serializer = DeptHeadIssueSerializer(issues, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)