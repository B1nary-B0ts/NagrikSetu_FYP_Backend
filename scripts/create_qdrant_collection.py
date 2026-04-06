from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="localhost", port=6333)

client.create_collection(
    collection_name="issues",
    vectors_config=VectorParams(
        size=512,        # ← CLIP embedding dimension
        distance=Distance.COSINE,
    ),
)

print("Collection created!")