import http.client
import io
import ipaddress
import os
import socket
import ssl
import time
import uuid
from urllib.parse import quote, urljoin, urlsplit

from PIL import Image

from config import settings

MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
UPLOAD_DIR = os.path.join(settings.data_dir, "uploads")

MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024  # largest source image accepted from a URL
MAX_REDIRECTS = 5
FETCH_TIMEOUT = 10  # seconds per socket operation
FETCH_DEADLINE = 30  # seconds for the whole download

# Global-looking IPv6 ranges that translate to IPv4 and could reach an internal address
_TRANSLATION_NETS = [ipaddress.ip_network("64:ff9b::/96"), ipaddress.ip_network("2002::/16")]

_UNREACHABLE = "That address can't be reached"
_BAD_URL = "URL must start with http:// or https://"


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


class ImageFetchError(Exception):
    """A URL could not be downloaded as an image. The message is safe to show to users."""


def _is_public_ip(ip) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (
        ip.is_global
        and not ip.is_multicast
        and not any(ip in net for net in _TRANSLATION_NETS)
    )


def _resolve_public_ips(host: str, port: int) -> list:
    """Resolve a host, refusing it if any of its addresses is not a public one."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        # Same message as a blocked address so internal host names can't be probed
        raise ImageFetchError(_UNREACHABLE)
    ips = [info[4][0] for info in infos]
    if not ips or not all(_is_public_ip(ipaddress.ip_address(ip.split("%")[0])) for ip in ips):
        raise ImageFetchError(_UNREACHABLE)
    return ips


def _connect(ips: list, port: int, timeout: float) -> socket.socket:
    error = OSError("no addresses to connect to")
    for ip in ips:
        try:
            return socket.create_connection((ip, port), timeout)
        except OSError as e:
            error = e
    raise error


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Connects to the already-validated addresses instead of resolving the host again,
    so DNS can't swap in an internal address between the check and the connection."""

    def __init__(self, host, port, ips, timeout):
        super().__init__(host, port, timeout=timeout)
        self._ips = ips

    def connect(self):
        self.sock = _connect(self._ips, self.port, self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, ips, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ips = ips

    def connect(self):
        sock = _connect(self._ips, self.port, self.timeout)
        try:
            # The certificate is still verified against the host name, not the pinned IP
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _read_limited(resp, limit: int, deadline: float) -> bytes:
    chunks, total = [], 0
    while True:
        if time.monotonic() > deadline:
            raise ImageFetchError("The download took too long")
        chunk = resp.read(64 * 1024)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > limit:
            raise ImageFetchError("The image is too large")
        chunks.append(chunk)


def fetch_image_bytes(url: str) -> bytes:
    """Download a URL over http(s), refusing internal addresses, and return the body.

    Redirects are followed by hand so every hop goes through the same checks.
    Raises ImageFetchError for anything refused or failed.
    """
    deadline = time.monotonic() + FETCH_DEADLINE
    url = url.strip()
    for _ in range(MAX_REDIRECTS + 1):
        parts = urlsplit(url)
        try:
            port = parts.port
        except ValueError:
            raise ImageFetchError(_BAD_URL)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ImageFetchError(_BAD_URL)
        https = parts.scheme == "https"
        port = port or (443 if https else 80)
        ips = _resolve_public_ips(parts.hostname, port)

        # Percent-encode spaces and non-ASCII characters, keeping existing %XX escapes
        target = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        if parts.query:
            target += "?" + quote(parts.query, safe="/%:@!$&'()*+,;=-._~?")

        conn_cls = _PinnedHTTPSConnection if https else _PinnedHTTPConnection
        conn = conn_cls(parts.hostname, port, ips, FETCH_TIMEOUT)
        try:
            conn.request("GET", target, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "*/*",
            })
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location")
                if not location:
                    raise ImageFetchError("The redirect had no destination")
                url = urljoin(url, location)
                continue
            if resp.status != 200:
                raise ImageFetchError("The server answered with HTTP %d" % resp.status)
            declared = resp.getheader("Content-Length", "")
            if declared.isdigit() and int(declared) > MAX_DOWNLOAD_BYTES:
                raise ImageFetchError("The image is too large")
            return _read_limited(resp, MAX_DOWNLOAD_BYTES, deadline)
        except (OSError, http.client.HTTPException):
            raise ImageFetchError("The download failed")
        finally:
            conn.close()
    raise ImageFetchError("Too many redirects")


def save_photo_from_url(image_url: str) -> str:
    """Download an image from a URL and save it locally. Returns filename.

    Raises ImageFetchError if the URL is refused, can't be downloaded, or isn't an image.
    """
    data = fetch_image_bytes(image_url)
    try:
        return save_photo(data, "web-image.jpg")
    except (OSError, Image.DecompressionBombError):
        raise ImageFetchError("That URL did not return a usable image")
