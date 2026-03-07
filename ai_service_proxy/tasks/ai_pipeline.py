from celery import shared_task
import logging

from issues.models import IssueReport
from departments.models import Department, DepartmentHead
from ai_service_proxy.services.ollama_vision_service import analyze_civic_issue

logger = logging.getLogger(__name__)


# -----------------------------
# Helper functions (same file)
# -----------------------------

def map_severity(ai_severity):
    """
    AI may return:
    - int (1–5)
    - string ("LOW", "HIGH", etc.)

    We normalize it to Issue.severity choices.
    """
    if ai_severity is None:
        return None

    # Case 1: numeric severity
    if isinstance(ai_severity, int):
        if ai_severity <= 2:
            return "LOW"
        elif ai_severity == 3:
            return "MEDIUM"
        elif ai_severity == 4:
            return "HIGH"
        else:
            return "CRITICAL"

    # Case 2: string severity
    ai_severity = str(ai_severity).upper().strip()
    if ai_severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return ai_severity

    return "MEDIUM"


def resolve_department(dept_name):
    if not dept_name:
        return None

    return Department.objects.filter(
        name__iexact=dept_name.strip()
    ).first()


def resolve_department_head(issue, department):
    """
    Priority:
    1. Ward-level department head
    2. Municipal-corp-level department head
    """
    if not department:
        return None

    # 1️⃣ Ward-level
    # Ward-level first (future use when ward boundary data is available)
    if issue.ward:
        dept_head = DepartmentHead.objects.filter(
            dept=department,
            ward=issue.ward,
            municipal_corp=issue.municipal_corp
        ).select_related("user").first()

    if dept_head:
        return dept_head

    # 2️⃣ Municipal fallback
    return DepartmentHead.objects.filter(
        dept=department,
        ward__isnull=True,
        municipal_corp=issue.municipal_corp
    ).select_related("user").first()


# -----------------------------
# Celery Task
# -----------------------------

@shared_task(
    bind=True,
    queue="ai_queue",
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 2},
)
def run_ai_pipeline(self, issue_report_id):
    logger.info(f"[AI PIPELINE] Started for issue_report={issue_report_id}")

    issue_report = IssueReport.objects.select_related(
        "issue", "citizen", "issue__ward", "issue__municipal_corp"
    ).get(id=issue_report_id)

    issue = issue_report.issue

    department_choices = list(
        Department.objects.values_list("name", flat=True)
    )

    # 1️⃣ Ollama Vision call (LOCAL image path)
    result = analyze_civic_issue(
        image_path=issue_report.local_image_path,
        description=issue_report.description or "",
        department_choices=department_choices,
    )

    logger.info(f"[AI PIPELINE] Ollama result: {result}")

    # 2️⃣ Image ↔ description validation
    if not result.get("match", False):
        issue.status = "NEEDS_CONFIRMATION"
        issue_report.is_mismatch = True

        issue.save(update_fields=["status"])
        issue_report.save(update_fields=["is_mismatch"])

        logger.warning(
            f"[AI PIPELINE] Mismatch detected "
            f"for issue_report={issue_report_id}"
        )

        return {"status": "image_description_mismatch"}

    # 3️⃣ Resolve Department
    department = resolve_department(result.get("department"))
    if not department:
        # safety fallback in case Ollama hallucinated despite instructions
        logger.warning(f"[AI PIPELINE] Department not found: {result.get('department')}")
    issue.dept = department

    # 4️⃣ Resolve Department Head
    dept_head = resolve_department_head(issue, department)
    issue.dept_head = dept_head

    # 5️⃣ Severity mapping
    issue.severity = map_severity(result.get("severity"))

    # 6️⃣ Status transition
    if department and dept_head:
        issue.status = "ASSIGNED"
    else:
        issue.status = "PROCESSING"

    issue.save(
        update_fields=["dept", "dept_head", "severity", "status"]
    )

    logger.info(
        f"[AI PIPELINE] Completed | "
        f"Issue={issue.id} | "
        f"Dept={department} | "
        f"Head={dept_head} | "
        f"Severity={issue.severity}"
    )

    return {
        "status": "ai_completed",
        "issue_id": issue.id,
        "department": department.name if department else None,
        "severity": issue.severity,
        "dept_head": dept_head.user.name if dept_head else None,
    }



# from celery import shared_task
# import logging

# from issues.models import IssueReport
# from ai_service_proxy.services.ollama_vision_service import analyze_civic_issue

# logger = logging.getLogger(__name__)


# @shared_task(
#     bind=True,
#     queue="ai_queue",
#     autoretry_for=(Exception,),
#     retry_backoff=30,
#     retry_kwargs={"max_retries": 2},
# )
# def run_ai_pipeline(self, issue_report_id):
#     logger.info(f"[AI PIPELINE] Started for issue_report={issue_report_id}")

#     issue_report = IssueReport.objects.select_related(
#         "issue", "citizen"
#     ).get(id=issue_report_id)

#     # 1️⃣ Call Ollama Vision
#     result = analyze_civic_issue(
#         image_url=issue_report.local_image_path,
#         description=issue_report.description or "",
#     )

#     logger.info(f"[AI PIPELINE] Ollama result: {result}")

#     issue = issue_report.issue

#     # 2️⃣ Image ↔ description validation
#     if not result.get("match", False):
#         issue.status = "NEEDS_CONFIRMATION"
#         issue.save(update_fields=["status"])
#         logger.warning(
#             f"[AI PIPELINE] Mismatch detected for issue_report={issue_report_id}"
#         )

#         return {"status": "image description mismatch"}

#     # 3️⃣ Severity + department
#     # issue = issue_report.issue
#     # issue.severity = result.get("severity")
#     # issue.dept = result.get("department")  # or FK mapping later
#     # issue.save(update_fields=["severity", "dept"])

#     # logger.info(
#     #     f"[AI PIPELINE] Completed for issue_report={issue_report_id}"
#     # )

#     return {
#         "status": "ai_completed",
#         "severity": issue.severity,
#         "department": issue.dept_name,
#     }
