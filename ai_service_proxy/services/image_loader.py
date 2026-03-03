from PIL import Image
import requests
from io import BytesIO
from pathlib import Path


def load_issue_image(issue_report):
    if issue_report.local_image_path:
        path = Path(issue_report.local_image_path)
        if path.exists():
            return Image.open(path).convert("RGB")

    if issue_report.image_url:
        response = requests.get(issue_report.image_url, timeout=5)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")

    raise ValueError("No image source available for issue report")
