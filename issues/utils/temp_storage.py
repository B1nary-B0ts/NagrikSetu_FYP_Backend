import uuid
from pathlib import Path
from django.conf import settings

def save_temp_image(uploaded_file) -> str:
    temp_dir = Path(settings.BASE_DIR) / "tmp" / "issue_reports"
    temp_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}.jpg"
    path = temp_dir / filename

    with open(path, "wb+") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    return str(path)


import os

def delete_temp_image(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        # never fail business flow because of cleanup
        pass
