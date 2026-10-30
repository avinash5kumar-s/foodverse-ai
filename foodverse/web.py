"""Web-layer logic, kept free of any web framework so it is easy to test."""

from __future__ import annotations

from .agent import FoodVerseAgent

MAX_UPLOAD_BYTES = 4_000_000  # Vercel request bodies are capped at ~4.5 MB


class RequestError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def analyze(text: str, image_bytes: bytes | None, agent: FoodVerseAgent | None = None) -> dict:
    """Run one stateless analysis and return a JSON-serialisable dict."""
    text = (text or "").strip()
    if not text and not image_bytes:
        raise RequestError("Send a meal description, a photo, or both.")
    if image_bytes and len(image_bytes) > MAX_UPLOAD_BYTES:
        raise RequestError("Image is too large (max 4 MB).", 413)

    if agent is None:
        try:
            agent = FoodVerseAgent()
        except RuntimeError as e:  # missing API key
            raise RequestError(str(e), 500) from e

    try:
        result = agent.ask(text, image_bytes)
    except Exception as e:  # noqa: BLE001 - surface a clean message to the browser
        raise RequestError(f"The model request failed: {e}", 502) from e
    return {"answer": result.text, "tool_calls": result.tool_calls}
