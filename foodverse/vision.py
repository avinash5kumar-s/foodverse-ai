"""Image helpers: validate, downscale, and encode for Groq's OpenAI-compatible API."""

from __future__ import annotations

import base64
import io
from PIL import Image
from .config import MAX_IMAGE_DIM

SUPPORTED = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}


def prepare_image(data: bytes) -> dict:
    """Return an OpenAI-compatible image_url content block from raw bytes."""
    img = Image.open(io.BytesIO(data))
    fmt = (img.format or "").upper()
    img.load()
    if max(img.size) > MAX_IMAGE_DIM:
        img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))
        fmt = "JPEG" if fmt not in ("PNG", "WEBP") else fmt
    if fmt not in SUPPORTED:
        fmt = "PNG"
    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{SUPPORTED[fmt]};base64,{encoded}"}}
