from ai_service_proxy.services.clip_service import ClipService
from ai_service_proxy.services.image_loader import load_issue_image
from geo import models
from issues.models import IssueReport
import torch
import numpy as np
from PIL import Image


def generate_embedding(issue_report: IssueReport):
    model, preprocess = ClipService.get_model()

    #image = Image.open(issue_report.local_image_path).convert("RGB")
    image = load_issue_image(issue_report)
    image_tensor = preprocess(image).unsqueeze(0)

    text = issue_report.description or ""
    text_tokens = np.clip.tokenize([text])

    with torch.no_grad():
        image_features = model.encode_image(image_tensor)
        text_features = model.encode_text(text_tokens)

        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        # Joint embedding (simple + effective)
        embedding = (image_features + text_features) / 2
        embedding /= embedding.norm(dim=-1, keepdim=True)

    return embedding.cpu().numpy()[0]



from ai_service_proxy.services.qdrant_service import client, COLLECTION_NAME
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def search_duplicates(embedding, issue, top_k=5):
    """
    Searches for duplicate issues using:
    - CLIP embedding similarity
    - Ward + municipal corporation filter
    - Geo-distance sanity check

    Returns:
        (duplicate_issue_id | None, similarity_score | None)
    """

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k,
        with_payload=True,
        score_threshold=0.85,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="ward_id",
                    match=MatchValue(value=issue.ward_id),
                ),
                FieldCondition(
                    key="municipal_corp_id",
                    match=MatchValue(value=issue.municipal_corp_id),
                ),
            ]
        ),
    )

    for hit in results:
        payload = hit.payload

        # Defensive checks (important in early development)
        if not payload:
            continue

        distance_km = haversine_distance(
            float(issue.latitude),
            float(issue.longitude),
            payload["latitude"],
            payload["longitude"],
        )

        # Final geo gate
        if distance_km <= 0.5:  # 500 meters
            return payload["issue_id"], hit.score

    return None, None
