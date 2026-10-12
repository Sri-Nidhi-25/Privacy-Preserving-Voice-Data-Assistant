import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import logging

from app.config import settings
from app.failure import PipelineError
from app.routers import health, data, voice
from app.utils.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# Configurable CORS origins (defaulting to localhost origins for local dev)
allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error processing request: %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An internal server error occurred."},
    )


@app.on_event("startup")
def on_startup():
    logger.info("Application starting up with model STT=%s, LLM=%s", settings.STT_MODEL, settings.OLLAMA_MODEL)


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
 
 
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)