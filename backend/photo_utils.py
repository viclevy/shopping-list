import io
import os
import uuid

from PIL import Image

from config import settings

MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
UPLOAD_DIR = os.path.join(settings.data_dir, "uploads")


def save_photo(file_bytes: bytes, original_name: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")

    # Resize large images first
    max_dim = 2048
    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim))

    # Iteratively reduce quality until under 2MB
    quality = 85
    buffer = io.BytesIO()
    while quality > 10:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        if buffer.tell() <= MAX_SIZE_BYTES:
            break
        quality -= 10
        if quality <= 30:
            img = img.resize((img.width // 2, img.height // 2))
            quality = 85

    filename = "%s.jpg" % uuid.uuid4().hex
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(buffer.getvalue())
    return filename


def delete_photo(filename: str):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
