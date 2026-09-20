import io
from datetime import datetime, timedelta, timezone

from PIL import Image


def hours_ago(hours):
    """A UTC ISO timestamp with a 'Z', the way the browser sends purchase times."""
    moment = datetime.now(timezone.utc) - timedelta(hours=hours)
    return moment.isoformat().replace("+00:00", "Z")


def jpeg(width=600, height=1400, orientation=None):
    """A plain JPEG, optionally carrying an EXIF orientation like a phone photo does."""
    image = Image.new("RGB", (width, height), (250, 250, 250))
    buffer = io.BytesIO()
    if orientation:
        exif = image.getexif()
        exif[0x0112] = orientation
        image.save(buffer, "JPEG", exif=exif)
    else:
        image.save(buffer, "JPEG")
    return buffer.getvalue()
