import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, data, voice
from app.utils.logging import configure_logging
 
configure_logging()

app = FastAPI(title="Privacy-Preserving Voice Data Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Dev-only: allows a local HTML test page (different origin) to call this API.
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

