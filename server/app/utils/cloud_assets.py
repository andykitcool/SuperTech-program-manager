import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

from app.services.storage_service import get_storage_service


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


def normalize_image_extension(filename: str, content_type: Optional[str]) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return ext
    if content_type == "image/svg+xml":
        return ".svg"
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    if content_type == "image/gif":
        return ".gif"
    return ".jpg"


def build_image_storage_key(prefix: str, filename: str, content_type: Optional[str]) -> str:
    ext = normalize_image_extension(filename, content_type)
    return f"{prefix.strip('/')}/{uuid.uuid4().hex}{ext}"


async def upload_image_to_cloud(
    file: UploadFile,
    *,
    prefix: str,
    allowed_extensions: Optional[set[str]] = None,
) -> dict[str, str]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = normalize_image_extension(file.filename or "", file.content_type)
    if allowed_extensions and ext not in allowed_extensions:
        ext = ".jpg"

    storage = get_storage_service()
    if not storage:
        raise HTTPException(status_code=500, detail="Cloud storage is not configured")

    data = await file.read()
    key = f"{prefix.strip('/')}/{uuid.uuid4().hex}{ext}"
    url = await storage.upload_file(data, key, content_type=file.content_type)
    filename = Path(key).name
    return {"url": url, "filename": filename, "storage_url": url, "storage_key": key}
