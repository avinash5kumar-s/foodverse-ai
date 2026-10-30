"""Vercel entrypoint. Exposes a top-level ASGI variable named `app`.

Local run:   uvicorn app:app --reload
Deploy:      push to Vercel; set GROQ_API_KEY in Project Settings -> Environment Variables.
(The Streamlit UI now lives in streamlit_app.py and is for local use only.)
"""

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from foodverse.page import INDEX_HTML
from foodverse.web import RequestError, analyze

app = FastAPI(title="Food Verse AI")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/analyze")
async def analyze_endpoint(text: str = Form(""), image: UploadFile | None = File(None)):
    data = await image.read() if image is not None else None
    try:
        return analyze(text, data or None)
    except RequestError as e:
        return JSONResponse({"error": e.message}, status_code=e.status)
