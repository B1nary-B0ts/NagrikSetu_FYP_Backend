# geo/views.py (dashboard section)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import (
    Count, Avg, F, ExpressionWrapper,
    DurationField, Q, FloatField
)
from django.db.models.functions import ExtractHour
from datetime import timedelta

from geo.models import WardHead
from users.permissions import RolePermission    
from issues.models import Issue
from departments.models import Department, DepartmentHead, DepartmentWorker


# ── Auth ─────────────────────────────────────────────────────────────────────

# class WardHeadLoginView(APIView):
#     permission_classes = []

#     def post(self, request):
#         from django.contrib.auth import authenticate
#         email = request.data.get("email")
#         password = request.data.get("password")

#         if not email or not password:
#             return Response(
#                 {"error": "Email and password required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         user = authenticate(request, username=email, password=password)

#         if not user:
#             return Response(
#                 {"error": "Invalid credentials"},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )

#         if user.role != "ward_head":
#             return Response(
#                 {"error": "Access denied. Ward Head only."},
#                 status=status.HTTP_403_FORBIDDEN
#             )

#         try:
#             ward_head = WardHead.objects.select_related("ward").get(user=user)
#         except WardHead.DoesNotExist:
#             return Response(
#                 {"error": "Ward Head profile not found"},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         refresh = RefreshToken.for_user(user)

#         response = Response({
#             "message": "Login successful",
#             "user": {
#                 "id": user.id,
#                 "name": user.name,
#                 "email": user.email,
#                 "role": user.role,
#             },
#             "ward": {
#                 "id": ward_head.ward.id,
#                 "name": ward_head.ward.name,
#             }
#         }, status=status.HTTP_200_OK)

#         response.set_cookie(
#             key="access_token",
#             value=str(refresh.access_token),
#             httponly=True,
#             secure=not settings.DEBUG,
#             samesite="Lax"
#         )
#         response.set_cookie(
#             key="refresh_token",
#             value=str(refresh),
#             httponly=True,
#             secure=not settings.DEBUG,
#             samesite="Lax"
#         )
#         return response


# class WardHeadLogoutView(APIView):
#     permission_classes = [IsAuthenticated, IsWardHead]

#     def post(self, request):
#         try:
#             refresh_token = request.COOKIES.get("refresh_token")
#             if refresh_token:
#                 token = RefreshToken(refresh_token)
#                 token.blacklist()
#         except TokenError:
#             pass

#         response = Response(
#             {"message": "Logged out successfully"},
#             status=status.HTTP_200_OK
#         )
#         response.delete_cookie("access_token")
#         response.delete_cookie("refresh_token")
#         return response


# ── Helper ───────────────────────────────────────────────────────────────────

def get_ward_from_request(request):
    """Returns the Ward object for the logged-in ward head."""
    ward_head = WardHead.objects.select_related("ward").get(user=request.user)
    return ward_head.ward


# ── Dashboard Overview ────────────────────────────────────────────────────────

class WardDashboardOverviewView(APIView):
    """
    Summary cards for the dashboard header.
    Total issues, by status, by severity.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)
        issues = Issue.objects.filter(ward=ward)

        total = issues.count()

        status_breakdown = dict(
            issues.values_list("status")
                  .annotate(count=Count("id"))
                  .values_list("status", "count")
        )

        severity_breakdown = dict(
            issues.exclude(severity__isnull=True)
                  .values_list("severity")
                  .annotate(count=Count("id"))
                  .values_list("severity", "count")
        )

        active_statuses = ["PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"]
        active = issues.filter(status__in=active_statuses).count()
        resolved = issues.filter(status="RESOLVED").count()

        return Response({
            "ward": ward.name,
            "total_issues": total,
            "active_issues": active,
            "resolved_issues": resolved,
            "status_breakdown": status_breakdown,
            "severity_breakdown": severity_breakdown,
        })


# ── Critical & High Severity Issues ──────────────────────────────────────────

class CriticalHighIssuesView(APIView):
    """
    Lists all HIGH and CRITICAL severity issues in the ward
    that are not yet resolved.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)

        issues = Issue.objects.filter(
            ward=ward,
            severity__in=["HIGH", "CRITICAL"],
            status__in=["PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"]
        ).select_related("dept", "dept_head__user").prefetch_related("workers__user")

        data = []
        for issue in issues:
            workers = [
                {"id": w.user.id, "name": w.user.name}
                for w in issue.workers.select_related("user").all()
            ]
            data.append({
                "issue_id": issue.id,
                "severity": issue.severity,
                "status": issue.status,
                "department": issue.dept.name if issue.dept else None,
                "dept_head": issue.dept_head.user.name if issue.dept_head else None,
                "assigned_workers": workers,
                "latitude": float(issue.latitude),
                "longitude": float(issue.longitude),
                "created_at": issue.created_at,
                "age_hours": round(
                    (timezone.now() - issue.created_at).total_seconds() / 3600, 1
                ),
            })

        # Sort: CRITICAL first, then HIGH, then oldest first
        severity_order = {"CRITICAL": 0, "HIGH": 1}
        data.sort(key=lambda x: (severity_order.get(x["severity"], 2), x["created_at"]))

        return Response({
            "count": len(data),
            "issues": data
        })


# ── Escalated Issues (SLA Breach > 72 hours) ─────────────────────────────────

class EscalatedIssuesView(APIView):
    """
    Issues that have been open for more than 72 hours without resolution.
    Also identifies which workers are responsible for the delay.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)
        sla_hours = int(request.query_params.get("sla_hours", 72))
        threshold = timezone.now() - timedelta(hours=sla_hours)

        escalated = Issue.objects.filter(
            ward=ward,
            created_at__lte=threshold,
            status__in=["PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"]
        ).select_related("dept", "dept_head__user").prefetch_related("workers__user")

        data = []
        for issue in escalated:
            age_hours = round(
                (timezone.now() - issue.created_at).total_seconds() / 3600, 1
            )
            workers = [
                {
                    "id": w.user.id,
                    "name": w.user.name,
                    "available": w.available,
                }
                for w in issue.workers.select_related("user").all()
            ]
            data.append({
                "issue_id": issue.id,
                "severity": issue.severity,
                "status": issue.status,
                "department": issue.dept.name if issue.dept else None,
                "dept_head": issue.dept_head.user.name if issue.dept_head else None,
                "assigned_workers": workers,
                "no_worker_assigned": len(workers) == 0,
                "latitude": float(issue.latitude),
                "longitude": float(issue.longitude),
                "created_at": issue.created_at,
                "age_hours": age_hours,
                "sla_breach_hours": round(age_hours - sla_hours, 1),
            })

        # Sort by most overdue first
        data.sort(key=lambda x: x["age_hours"], reverse=True)

        return Response({
            "sla_hours": sla_hours,
            "escalated_count": len(data),
            "issues": data
        })


# ── Worker Performance ────────────────────────────────────────────────────────

class WorkerPerformanceView(APIView):
    """
    Per-worker breakdown:
    - How many issues assigned
    - How many resolved
    - How many still pending
    - Average resolution time
    - How many escalated issues they are on
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)
        threshold = timezone.now() - timedelta(hours=72)

        # Get all workers whose dept_head is in this ward
        workers = DepartmentWorker.objects.filter(
            dept_head__ward=ward
        ).select_related("user", "dept_head__dept")

        data = []
        for worker in workers:
            assigned_issues = Issue.objects.filter(workers=worker, ward=ward)
            total = assigned_issues.count()
            resolved = assigned_issues.filter(status="RESOLVED").count()
            pending = assigned_issues.filter(
                status__in=["ASSIGNED", "IN_PROGRESS"]
            ).count()
            escalated = assigned_issues.filter(
                created_at__lte=threshold,
                status__in=["ASSIGNED", "IN_PROGRESS"]
            ).count()

            # Average resolution time in hours for resolved issues
            resolved_issues = assigned_issues.filter(
                status="RESOLVED",
                resolved_at__isnull=False
            )
            avg_resolution_hours = None
            if resolved_issues.exists():
                avg_duration = resolved_issues.annotate(
                    duration=ExpressionWrapper(
                        F("resolved_at") - F("created_at"),
                        output_field=DurationField()
                    )
                ).aggregate(avg=Avg("duration"))["avg"]
                if avg_duration:
                    avg_resolution_hours = round(
                        avg_duration.total_seconds() / 3600, 1
                    )

            data.append({
                "worker_id": worker.user.id,
                "worker_name": worker.user.name,
                "department": worker.dept_head.dept.name,
                "available": worker.available,
                "total_assigned": total,
                "resolved": resolved,
                "pending": pending,
                "escalated_count": escalated,
                "avg_resolution_hours": avg_resolution_hours,
                "resolution_rate": round(
                    (resolved / total * 100), 1
                ) if total > 0 else 0,
            })

        # Sort by escalated count descending — worst performers first
        data.sort(key=lambda x: x["escalated_count"], reverse=True)

        return Response({
            "ward": ward.name,
            "total_workers": len(data),
            "workers": data
        })


# ── Department Load Analysis ──────────────────────────────────────────────────

class DepartmentLoadView(APIView):
    """
    Which department is receiving the most issues.
    Resolution rate per department.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)

        dept_stats = (
            Issue.objects.filter(ward=ward, dept__isnull=False)
            .values("dept__id", "dept__name")
            .annotate(
                total=Count("id"),
                resolved=Count("id", filter=Q(status="RESOLVED")),
                critical=Count("id", filter=Q(severity="CRITICAL")),
                high=Count("id", filter=Q(severity="HIGH")),
                pending=Count(
                    "id",
                    filter=Q(status__in=[
                        "PROCESSING", "NEEDS_CONFIRMATION",
                        "ASSIGNED", "IN_PROGRESS"
                    ])
                ),
            )
            .order_by("-total")
        )

        data = []
        for dept in dept_stats:
            total = dept["total"]
            resolved = dept["resolved"]
            data.append({
                "department_id": dept["dept__id"],
                "department_name": dept["dept__name"],
                "total_issues": total,
                "resolved": resolved,
                "pending": dept["pending"],
                "critical_issues": dept["critical"],
                "high_issues": dept["high"],
                "resolution_rate": round(
                    (resolved / total * 100), 1
                ) if total > 0 else 0,
            })

        return Response({
            "ward": ward.name,
            "departments": data
        })


# ── Geographic Hotspots ───────────────────────────────────────────────────────

class GeographicHotspotView(APIView):
    """
    Heatmap data — lat/lng points with severity weight.
    Active issues only.
    Optional filter by department or severity.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    SEVERITY_WEIGHTS = {"LOW": 1, "MEDIUM": 2, "HIGH": 4, "CRITICAL": 8}
    ACTIVE_STATUSES = ["PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"]

    def get(self, request):
        ward = get_ward_from_request(request)

        dept_id = request.query_params.get("dept_id")
        severity = request.query_params.get("severity")

        issues = Issue.objects.filter(
            ward=ward,
            status__in=self.ACTIVE_STATUSES
        )

        if dept_id:
            issues = issues.filter(dept_id=dept_id)
        if severity:
            severities = [s.strip().upper() for s in severity.split(",")]
            issues = issues.filter(severity__in=severities)

        points = [
            {
                "latitude": float(issue["latitude"]),
                "longitude": float(issue["longitude"]),
                "weight": self.SEVERITY_WEIGHTS.get(issue["severity"], 1),
                "severity": issue["severity"],
            }
            for issue in issues.values("latitude", "longitude", "severity")
        ]

        return Response({
            "ward": ward.name,
            "total_points": len(points),
            "points": points
        })


# ── Department Head Overview ──────────────────────────────────────────────────

class DepartmentHeadOverviewView(APIView):
    """
    All department heads in the ward with their team size
    and issue resolution stats.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)

        dept_heads = DepartmentHead.objects.filter(
            ward=ward
        ).select_related("user", "dept")

        data = []
        for head in dept_heads:
            issues = Issue.objects.filter(dept_head=head, ward=ward)
            total = issues.count()
            resolved = issues.filter(status="RESOLVED").count()
            escalated = issues.filter(
                created_at__lte=timezone.now() - timedelta(hours=72),
                status__in=["ASSIGNED", "IN_PROGRESS", "NEEDS_CONFIRMATION"]
            ).count()
            worker_count = DepartmentWorker.objects.filter(dept_head=head).count()

            data.append({
                "dept_head_id": head.user.id,
                "dept_head_name": head.user.name,
                "email": head.user.email,
                "department": head.dept.name,
                "worker_count": worker_count,
                "total_issues": total,
                "resolved": resolved,
                "escalated": escalated,
                "resolution_rate": round(
                    (resolved / total * 100), 1
                ) if total > 0 else 0,
            })

        data.sort(key=lambda x: x["escalated"], reverse=True)

        return Response({
            "ward": ward.name,
            "dept_heads": data
        })


# ── Resolution Time Trends ────────────────────────────────────────────────────

class ResolutionTimeTrendsView(APIView):
    """
    Average resolution time per department.
    Helps identify which departments are slowest.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["ward_head"]

    def get(self, request):
        ward = get_ward_from_request(request)

        resolved_issues = Issue.objects.filter(
            ward=ward,
            status="RESOLVED",
            resolved_at__isnull=False,
            dept__isnull=False
        ).annotate(
            resolution_duration=ExpressionWrapper(
                F("resolved_at") - F("created_at"),
                output_field=DurationField()
            )
        )

        # Group by department
        dept_map = {}
        for issue in resolved_issues.select_related("dept"):
            dept_name = issue.dept.name
            hours = issue.resolution_duration.total_seconds() / 3600
            if dept_name not in dept_map:
                dept_map[dept_name] = []
            dept_map[dept_name].append(hours)

        data = [
            {
                "department": dept,
                "resolved_count": len(hours_list),
                "avg_resolution_hours": round(
                    sum(hours_list) / len(hours_list), 1
                ),
                "min_hours": round(min(hours_list), 1),
                "max_hours": round(max(hours_list), 1),
            }
            for dept, hours_list in dept_map.items()
        ]

        data.sort(key=lambda x: x["avg_resolution_hours"], reverse=True)

        return Response({
            "ward": ward.name,
            "department_resolution_times": data
        })