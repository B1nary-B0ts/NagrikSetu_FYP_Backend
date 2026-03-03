import cloudinary
import cloudinary.uploader
from django.conf import settings

# Initialize once
cloudinary.config(
    cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
    api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
    api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
    secure=True,
)


def upload_image(file, folder="issue_reports"):
    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        resource_type="image",
        overwrite=False,
    )

    return {
        "secure_url": result["secure_url"],
        "public_id": result["public_id"],
    }
