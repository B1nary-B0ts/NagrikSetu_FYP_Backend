from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
client = QdrantClient(
    host="localhost",
    port=6333
)

COLLECTION_NAME = "issues"
