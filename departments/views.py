from django.shortcuts import render
from django.db.models import Count, Case, When, IntegerField
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from departments.models import DepartmentWorker
from issues.models import Issue
from .serializers import DepartmentWorkerAssignSerializer, DeptHeadIssueSerializer, DepartmentWorkerSerializer, WorkerIssueSerializer
from django.utils import timezone
from issues.utils.cloudinary import upload_image
from issues.utils.temp_storage import save_temp_image
from ai_service_proxy.tasks.ai_pipeline import verify_issue_resolution
import math
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
    
class WorkerIssuesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != "dept_worker":
            return Response(
                {"error": "Only department workers can access this"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            worker = user.dept_worker_profile  # OneToOne related_name
        except Exception:
            return Response(
                {"error": "Worker profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # fetch issues where this worker is assigned
        issues = Issue.objects.filter(
            workers=worker  # ← ManyToMany lookup
        ).select_related(
            "ward", "municipal_corp", "dept"
        ).order_by("-created_at")

        serializer = WorkerIssueSerializer(issues, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class ResolveIssueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, issue_id):
        user = request.user

        if user.role != "dept_worker":
            return Response(
                {"error": "Only department workers can resolve issues"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            worker = user.dept_worker_profile
        except Exception:
            return Response(
                {"error": "Worker profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            issue = Issue.objects.get(id=issue_id, workers=worker)
        except Issue.DoesNotExist:
            return Response(
                {"error": "Issue not found or not assigned to you"},
                status=status.HTTP_404_NOT_FOUND
            )

        if issue.status != "IN_PROGRESS":
            return Response(
                {"error": f"Issue is not in progress, current status: {issue.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Location validation ──────────────────────────────────────
        try:
            worker_lat = float(request.data.get("latitude"))
            worker_lon = float(request.data.get("longitude"))
        except (TypeError, ValueError):
            return Response(
                {"error": "latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        distance_meters = haversine_distance(
            worker_lat, worker_lon,
            float(issue.latitude), float(issue.longitude)
        )

        ALLOWED_RADIUS_METERS = 50  # ← adjust as needed

        if distance_meters > ALLOWED_RADIUS_METERS:
            return Response(
                {
                    "error": "Location mismatch — you are not at the issue location",
                    "your_location": {"latitude": worker_lat, "longitude": worker_lon},
                    "issue_location": {"latitude": float(issue.latitude), "longitude": float(issue.longitude)},
                    "distance_meters": round(distance_meters, 2),
                    "allowed_radius_meters": ALLOWED_RADIUS_METERS,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # ── End location validation ──────────────────────────────────

        after_image = request.FILES.get("after_image")
        if not after_image:
            return Response(
                {"error": "after_image is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        local_after_image_path = save_temp_image(after_image)
        with open(local_after_image_path, "rb") as f:
            upload_result = upload_image(f)
        after_image_url = upload_result["secure_url"]

        before_report = issue.reports.filter(is_duplicate=False).first()
        if not before_report:
            return Response(
                {"error": "No original report image found for comparison"},
                status=status.HTTP_400_BAD_REQUEST
            )

        issue.after_image_url = after_image_url
        issue.save(update_fields=["after_image_url"])

        verify_issue_resolution.delay(
            issue_id=issue.id,
            before_image_path=before_report.local_image_path,
            after_image_path=local_after_image_path,
            description=before_report.description or "",
        )

        return Response(
            {
                "message": "After image uploaded, AI verification in progress",
                "issue_id": issue.id,
                "distance_meters": round(distance_meters, 2),
            },
            status=status.HTTP_202_ACCEPTED
        )
