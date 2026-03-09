from django.shortcuts import render
from django.db.models import Count, Case, When, IntegerField
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from departments.models import DepartmentWorker
from issues.models import Issue
from .serializers import DepartmentWorkerAssignSerializer, DeptHeadIssueSerializer, DepartmentWorkerSerializer
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
    
class AvailableWorkersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != "dept_head":
            return Response(
                {"error": "Only department heads can access this"},
                status = status.HTTP_403_FORBIDDEN
            )
        
        try:
            dept_head = user.dept_head_profile
        except Exception:
            return Response(
                {"error": "Department head profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        workers = DepartmentWorker.objects.filter(
            dept_head=dept_head,
            available=True
        ).select_related("user")

        serializer = DepartmentWorkerSerializer(workers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AssignWorkersView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, issue_id):
        user = request.user

        if user.role != "dept_head":
            return Response(
                {"error": "Only department heads can assign workers"},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            dept_head = user.dept_head_profile
        except Exception:
            return Response(
                {"error": "Department head profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        worker_ids = request.data.get("worker_ids", [])
        if not worker_ids or not isinstance(worker_ids, list):
            return Response(
                {"error": "worker_ids must be a non-empty list of worker IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            issue = Issue.objects.get(
                id=issue_id,
                dept=dept_head.dept,
                municipal_corp=dept_head.municipal_corp,
            )
        except Issue.DoesNotExist:
            return Response(
                {"error": "Issue not found or not assigned to your department"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        workers = DepartmentWorker.objects.filter(
            id__in=worker_ids,
            dept_head=dept_head,
            available=True
        )

        if workers.count() != len(worker_ids):
            return Response(
                {"error": "Some workers are not available or don't belong to your department"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        issue.workers.add(*workers)
        workers.update(available=False)

        issue.status = "IN_PROGRESS"
        issue.save(update_fields=["status"])

        return Response(
            {
                "message": f"{workers.count()} workers assigned to Issue #{issue.id}",
                "issue_id": issue.id,
                "status": issue.status,
                "assigned_workers": DepartmentWorkerAssignSerializer(workers, many=True).data
            },
            status=status.HTTP_200_OK
        )