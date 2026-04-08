# geo/views.py (municipal corp dashboard section)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import (
    Count, Avg, F, ExpressionWrapper,
    DurationField, Q
)
from datetime import timedelta

from geo.models import MunicipalCorpHead, Ward
from users.permissions import RolePermission
from issues.models import Issue
from departments.models import Department, DepartmentHead, DepartmentWorker


def get_corp_from_request(request):
    """Returns the MunicipalCorporation object for the logged-in corp head."""
    corp_head = MunicipalCorpHead.objects.select_related(
        "municipal_corp"
    ).get(user=request.user)
    return corp_head.municipal_corp


# ── 1. Overview ───────────────────────────────────────────────────────────────

class CorpDashboardOverviewView(APIView):
    """
    Top-level summary of the entire municipal corporation.
    Total issues across all wards, status breakdown, severity breakdown.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)
        issues = Issue.objects.filter(municipal_corp=corp)

        total = issues.count()
        active_statuses = [
            "PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"
        ]

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

        total_wards = Ward.objects.filter(municipal_corp=corp).count()
        total_workers = DepartmentWorker.objects.filter(
            dept_head__municipal_corp=corp
        ).count()
        total_dept_heads = DepartmentHead.objects.filter(
            municipal_corp=corp
        ).count()

        return Response({
            "municipal_corp": corp.name,
            "total_wards": total_wards,
            "total_dept_heads": total_dept_heads,
            "total_workers": total_workers,
            "total_issues": total,
            "active_issues": issues.filter(status__in=active_statuses).count(),
            "resolved_issues": issues.filter(status="RESOLVED").count(),
            "status_breakdown": status_breakdown,
            "severity_breakdown": severity_breakdown,
        })


# ── 2. Ward Comparison ────────────────────────────────────────────────────────

class WardComparisonView(APIView):
    """
    Side-by-side stats for every ward in the corporation.
    Answers: which ward has the most issues, worst resolution rate,
    most escalated issues, most critical issues.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)
        threshold = timezone.now() - timedelta(weeks=1)
        active_statuses = [
            "PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"
        ]

        wards = Ward.objects.filter(municipal_corp=corp)

        data = []
        for ward in wards:
            issues = Issue.objects.filter(ward=ward)
            total = issues.count()
            resolved = issues.filter(status="RESOLVED").count()
            active = issues.filter(status__in=active_statuses).count()
            critical = issues.filter(severity="CRITICAL").count()
            high = issues.filter(severity="HIGH").count()
            escalated = issues.filter(
                created_at__lte=threshold,
                status__in=active_statuses
            ).count()

            data.append({
                "ward_id": ward.id,
                "ward_name": ward.name,
                "total_issues": total,
                "active_issues": active,
                "resolved_issues": resolved,
                "critical_issues": critical,
                "high_issues": high,
                "escalated_issues": escalated,
                "resolution_rate": round(
                    (resolved / total * 100), 1
                ) if total > 0 else 0,
            })

        # Sort by total issues descending — most burdened ward first
        sort_by = request.query_params.get("sort_by", "total_issues")
        allowed_sorts = [
            "total_issues", "active_issues", "escalated_issues",
            "critical_issues", "resolution_rate"
        ]
        if sort_by in allowed_sorts:
            data.sort(key=lambda x: x[sort_by], reverse=True)

        return Response({
            "municipal_corp": corp.name,
            "total_wards": len(data),
            "wards": data
        })


# ── 3. Critical & High Issues Across All Wards ───────────────────────────────

class CorpCriticalHighIssuesView(APIView):
    """
    All HIGH and CRITICAL unresolved issues across every ward.
    Can filter by ward or severity.
    Helps corp head prioritise which wards need immediate attention.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)

        ward_id = request.query_params.get("ward_id")
        severity = request.query_params.get("severity")  # HIGH or CRITICAL or both

        issues = Issue.objects.filter(
            municipal_corp=corp,
            severity__in=["HIGH", "CRITICAL"],
            status__in=[
                "PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"
            ]
        ).select_related("ward", "dept", "dept_head__user")

        if ward_id:
            issues = issues.filter(ward_id=ward_id)
        if severity:
            severities = [s.strip().upper() for s in severity.split(",")]
            issues = issues.filter(severity__in=severities)

        data = []
        for issue in issues:
            data.append({
                "issue_id": issue.id,
                "ward": issue.ward.name if issue.ward else "Unassigned",
                "severity": issue.severity,
                "status": issue.status,
                "department": issue.dept.name if issue.dept else None,
                "dept_head": (
                    issue.dept_head.user.name if issue.dept_head else None
                ),
                "latitude": float(issue.latitude),
                "longitude": float(issue.longitude),
                "created_at": issue.created_at,
                "age_hours": round(
                    (timezone.now() - issue.created_at).total_seconds() / 3600,
                    1
                ),
            })

        severity_order = {"CRITICAL": 0, "HIGH": 1}
        data.sort(
            key=lambda x: (severity_order.get(x["severity"], 2), -x["age_hours"])
        )

        return Response({
            "municipal_corp": corp.name,
            "count": len(data),
            "issues": data
        })


# ── 4. Escalated Issues — Unresolved > 1 Week ────────────────────────────────

class CorpEscalatedIssuesView(APIView):
    """
    Issues unresolved for more than a week (configurable via sla_days param).
    Grouped by ward so corp head sees which wards are failing SLA.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)
        sla_days = int(request.query_params.get("sla_days", 7))
        threshold = timezone.now() - timedelta(days=sla_days)
        ward_id = request.query_params.get("ward_id")

        issues = Issue.objects.filter(
            municipal_corp=corp,
            created_at__lte=threshold,
            status__in=[
                "PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"
            ]
        ).select_related("ward", "dept", "dept_head__user").prefetch_related(
            "workers__user"
        )

        if ward_id:
            issues = issues.filter(ward_id=ward_id)

        # Group by ward
        ward_map = {}
        for issue in issues:
            ward_name = issue.ward.name if issue.ward else "Unassigned"
            ward_key = issue.ward_id or "none"

            if ward_key not in ward_map:
                ward_map[ward_key] = {
                    "ward_id": issue.ward_id,
                    "ward_name": ward_name,
                    "issues": []
                }

            workers = [
                {"id": w.user.id, "name": w.user.name}
                for w in issue.workers.select_related("user").all()
            ]
            age_days = round(
                (timezone.now() - issue.created_at).total_seconds() / 86400, 1
            )
            ward_map[ward_key]["issues"].append({
                "issue_id": issue.id,
                "severity": issue.severity,
                "status": issue.status,
                "department": issue.dept.name if issue.dept else None,
                "dept_head": (
                    issue.dept_head.user.name if issue.dept_head else None
                ),
                "assigned_workers": workers,
                "no_worker_assigned": len(workers) == 0,
                "age_days": age_days,
                "overdue_by_days": round(age_days - sla_days, 1),
                "created_at": issue.created_at,
            })

        result = list(ward_map.values())

        # Sort wards by number of escalated issues
        result.sort(key=lambda x: len(x["issues"]), reverse=True)
        for ward in result:
            ward["escalated_count"] = len(ward["issues"])
            ward["issues"].sort(key=lambda x: x["age_days"], reverse=True)

        return Response({
            "municipal_corp": corp.name,
            "sla_days": sla_days,
            "total_escalated": sum(w["escalated_count"] for w in result),
            "wards": result
        })


# ── 5. Issue Category (Department) Frequency Across Corp ─────────────────────

class CorpIssueCategoryFrequencyView(APIView):
    """
    Which type of civic issue (department category) is most frequent
    across the entire corp and broken down per ward.
    Answers: is garbage the top issue everywhere or just in specific wards?
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)
        ward_id = request.query_params.get("ward_id")

        issues = Issue.objects.filter(
            municipal_corp=corp,
            dept__isnull=False
        )
        if ward_id:
            issues = issues.filter(ward_id=ward_id)

        # Overall frequency across corp
        overall = (
            issues
            .values("dept__id", "dept__name")
            .annotate(
                total=Count("id"),
                resolved=Count("id", filter=Q(status="RESOLVED")),
                critical=Count("id", filter=Q(severity="CRITICAL")),
                high=Count("id", filter=Q(severity="HIGH")),
            )
            .order_by("-total")
        )

        overall_data = [
            {
                "department_id": d["dept__id"],
                "department_name": d["dept__name"],
                "total_issues": d["total"],
                "resolved": d["resolved"],
                "critical": d["critical"],
                "high": d["high"],
                "resolution_rate": round(
                    (d["resolved"] / d["total"] * 100), 1
                ) if d["total"] > 0 else 0,
            }
            for d in overall
        ]

        # Per-ward breakdown — which dept is top issue in each ward
        ward_breakdown = (
            issues
            .values("ward__id", "ward__name", "dept__name")
            .annotate(count=Count("id"))
            .order_by("ward__id", "-count")
        )

        ward_dept_map = {}
        for row in ward_breakdown:
            wid = row["ward__id"]
            if wid not in ward_dept_map:
                ward_dept_map[wid] = {
                    "ward_id": wid,
                    "ward_name": row["ward__name"],
                    "top_issue": row["dept__name"],  # first = highest count
                    "departments": []
                }
            ward_dept_map[wid]["departments"].append({
                "department": row["dept__name"],
                "count": row["count"]
            })

        return Response({
            "municipal_corp": corp.name,
            "overall_frequency": overall_data,
            "per_ward_breakdown": list(ward_dept_map.values())
        })


# ── 6. Geographic Hotspot Across Entire Corp ──────────────────────────────────

class CorpGeographicHotspotView(APIView):
    """
    Heatmap points for entire municipal corporation.
    Filter by ward, department, or severity.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    SEVERITY_WEIGHTS = {"LOW": 1, "MEDIUM": 2, "HIGH": 4, "CRITICAL": 8}
    ACTIVE_STATUSES = [
        "PROCESSING", "NEEDS_CONFIRMATION", "ASSIGNED", "IN_PROGRESS"
    ]

    def get(self, request):
        corp = get_corp_from_request(request)

        ward_id = request.query_params.get("ward_id")
        dept_id = request.query_params.get("dept_id")
        severity = request.query_params.get("severity")

        issues = Issue.objects.filter(
            municipal_corp=corp,
            status__in=self.ACTIVE_STATUSES
        )

        if ward_id:
            issues = issues.filter(ward_id=ward_id)
        if dept_id:
            issues = issues.filter(dept_id=dept_id)
        if severity:
            severities = [s.strip().upper() for s in severity.split(",")]
            issues = issues.filter(severity__in=severities)

        points = [
            {
                "latitude": float(i["latitude"]),
                "longitude": float(i["longitude"]),
                "weight": self.SEVERITY_WEIGHTS.get(i["severity"], 1),
                "severity": i["severity"],
                "ward_id": i["ward_id"],
            }
            for i in issues.values(
                "latitude", "longitude", "severity", "ward_id"
            )
        ]

        return Response({
            "municipal_corp": corp.name,
            "total_points": len(points),
            "points": points
        })


# ── 7. Department Performance Across Corp ────────────────────────────────────

class CorpDepartmentPerformanceView(APIView):
    """
    Per-department performance across entire corp.
    Avg resolution time, resolution rate, escalated count.
    Can filter by ward to see how a dept performs in a specific ward.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)
        ward_id = request.query_params.get("ward_id")
        threshold = timezone.now() - timedelta(weeks=1)

        issues = Issue.objects.filter(
            municipal_corp=corp,
            dept__isnull=False
        )
        if ward_id:
            issues = issues.filter(ward_id=ward_id)

        dept_stats = (
            issues
            .values("dept__id", "dept__name")
            .annotate(
                total=Count("id"),
                resolved=Count("id", filter=Q(status="RESOLVED")),
                escalated=Count(
                    "id",
                    filter=Q(
                        created_at__lte=threshold,
                        status__in=[
                            "PROCESSING", "NEEDS_CONFIRMATION",
                            "ASSIGNED", "IN_PROGRESS"
                        ]
                    )
                ),
                critical=Count("id", filter=Q(severity="CRITICAL")),
            )
            .order_by("-total")
        )

        # Avg resolution time per dept
        resolved_issues = issues.filter(
            status="RESOLVED",
            resolved_at__isnull=False
        ).annotate(
            duration=ExpressionWrapper(
                F("resolved_at") - F("created_at"),
                output_field=DurationField()
            )
        ).values("dept__id", "duration")

        dept_durations = {}
        for row in resolved_issues:
            did = row["dept__id"]
            hours = row["duration"].total_seconds() / 3600
            if did not in dept_durations:
                dept_durations[did] = []
            dept_durations[did].append(hours)

        data = []
        for d in dept_stats:
            did = d["dept__id"]
            total = d["total"]
            resolved = d["resolved"]
            durations = dept_durations.get(did, [])
            avg_hours = round(
                sum(durations) / len(durations), 1
            ) if durations else None

            data.append({
                "department_id": did,
                "department_name": d["dept__name"],
                "total_issues": total,
                "resolved": resolved,
                "escalated": d["escalated"],
                "critical_issues": d["critical"],
                "resolution_rate": round(
                    (resolved / total * 100), 1
                ) if total > 0 else 0,
                "avg_resolution_hours": avg_hours,
            })

        data.sort(key=lambda x: x["escalated"], reverse=True)

        return Response({
            "municipal_corp": corp.name,
            "departments": data
        })


# ── 8. Worker Performance Across Corp ────────────────────────────────────────

class CorpWorkerPerformanceView(APIView):
    """
    All workers across the corp with resolution stats.
    Filter by ward or department to narrow down.
    Identifies underperforming workers causing escalations.
    """
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = ["municipal_corp_head"]

    def get(self, request):
        corp = get_corp_from_request(request)
        ward_id = request.query_params.get("ward_id")
        dept_id = request.query_params.get("dept_id")
        threshold = timezone.now() - timedelta(weeks=1)

        workers = DepartmentWorker.objects.filter(
            dept_head__municipal_corp=corp
        ).select_related("user", "dept_head__dept", "dept_head__ward")

        if ward_id:
            workers = workers.filter(dept_head__ward_id=ward_id)
        if dept_id:
            workers = workers.filter(dept_head__dept_id=dept_id)

        data = []
        for worker in workers:
            assigned = Issue.objects.filter(
                workers=worker,
                municipal_corp=corp
            )
            total = assigned.count()
            resolved = assigned.filter(status="RESOLVED").count()
            escalated = assigned.filter(
                created_at__lte=threshold,
                status__in=["ASSIGNED", "IN_PROGRESS"]
            ).count()

            resolved_timed = assigned.filter(
                status="RESOLVED",
                resolved_at__isnull=False
            ).annotate(
                duration=ExpressionWrapper(
                    F("resolved_at") - F("created_at"),
                    output_field=DurationField()
                )
            )
            avg_hours = None
            if resolved_timed.exists():
                avg = resolved_timed.aggregate(
                    avg=Avg("duration")
                )["avg"]
                if avg:
                    avg_hours = round(avg.total_seconds() / 3600, 1)

            data.append({
                "worker_id": worker.user.id,
                "worker_name": worker.user.name,
                "department": worker.dept_head.dept.name,
                "ward": (
                    worker.dept_head.ward.name
                    if worker.dept_head.ward else "N/A"
                ),
                "available": worker.available,
                "total_assigned": total,
                "resolved": resolved,
                "escalated_count": escalated,
                "avg_resolution_hours": avg_hours,
                "resolution_rate": round(
                    (resolved / total * 100), 1
                ) if total > 0 else 0,
            })

        data.sort(key=lambda x: x["escalated_count"], reverse=True)

        return Response({
            "municipal_corp": corp.name,
            "total_workers": len(data),
            "workers": data
        })