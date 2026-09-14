import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import health, data, voice
from app.utils.logging import configure_logging
from fastapi.responses import FileResponse

configure_logging()

app = FastAPI(title="Privacy-Preserving Voice Data Assistant")

# Permissive CORS for cross-origin or local test clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(data.router)
app.include_router(voice.router)

os.makedirs("temp_audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="temp_audio"), name="static")

CHAT_UI_PATH = Path(__file__).resolve().parent.parent / "voice_chat.html"


@app.get("/")
def serve_chat_ui():
    """
    Serves voice_chat.html from the same origin as the API instead of it
    being opened as a bare file:// page. This matters beyond convenience:
    some browsers (notably Chromium-based ones) restrict or silently
    degrade navigator.mediaDevices.getUserMedia() on file:// origins, which
    was a likely contributor to "asks for mic permission but nothing
    happens" -- serving over http://127.0.0.1 avoids that class of issue
    entirely.
    """
    return FileResponse(CHAT_UI_PATH)