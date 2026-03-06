from celery import shared_task
from ai_service_proxy.tasks.ai_pipeline import run_ai_pipeline
from issues.models import Issue, IssueReport
from ai_service_proxy.tasks.deduplication import generate_embedding, search_duplicates
from ai_service_proxy.services.qdrant_service import client, COLLECTION_NAME
from qdrant_client.http.models import PointStruct
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 3},
)
def process_issue_report(self, issue_report_id, ward_id, municipal_corp_id, latitude, longitude):
    logger.info(f"[AI PIPELINE] Processing issue_report={issue_report_id}")

    issue_report = IssueReport.objects.select_related(
        #"issue",
         "citizen"
    ).get(id=issue_report_id)
    #issue = issue_report.issue

    # 1️⃣ Generate embedding
    embedding = generate_embedding(issue_report)
    if not embedding:
        raise ValueError("Failed to generate embedding")

    logger.info(f"Embedding generated (dim={len(embedding)})")

    # 2️⃣ Search for duplicates
    duplicate_issue_id, score = search_duplicates(embedding, #issue
                                                    ward_id, municipal_corp_id, latitude, longitude
                                                )

    if duplicate_issue_id:
        logger.info(
            f"Duplicate found → issue={duplicate_issue_id}, score={score}"
        )

        issue_report.issue_id = duplicate_issue_id
        issue_report.is_duplicate = True
        issue_report.match_score = score
        issue_report.duplicate_of_id = duplicate_issue_id
        issue_report.save(update_fields=["issue", "is_duplicate", "match_score", "duplicate_of"]
        )

        return {
            "issue_report_id": issue_report_id,
            "status": "duplicate",
            "duplicate_issue_id": duplicate_issue_id,
        }

    issue = Issue.objects.create(
        ward_id=ward_id,
        municipal_corp_id=municipal_corp_id,
        latitude=latitude,
        longitude=longitude,
        status="PROCESSING",
    )

    issue_report.issue = issue
    issue_report.save(update_fields=["issue"])

    # 3️⃣ No duplicate → upsert into Qdrant
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=issue_report.id,  # ✅ IMPORTANT
                vector=embedding,
                payload={
                    "issue_id": issue.id,
                    "issue_report_id": issue_report.id,
                    "ward_id": issue.ward_id,
                    "municipal_corp_id": issue.municipal_corp_id,
                    "latitude": float(issue.latitude),
                    "longitude": float(issue.longitude),
                },
            )
        ],
    )

    logger.info(f"Vector stored in Qdrant for issue_report={issue_report.id}")

    # 4️⃣ AI Pipeline 
    run_ai_pipeline.delay(issue_report.id)

    return {
        "issue_report_id": issue_report_id,
        "status": "processed",
        "issue_id": issue.id,
    }
