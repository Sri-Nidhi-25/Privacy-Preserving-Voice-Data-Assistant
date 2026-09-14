"""
app/routers/health.py - Liveness and readiness endpoints.

/health/live  - Is the process alive?   (lightweight, no dependency checks)
/health/ready - Can it process requests? (checks Whisper, Ollama, TTS, data files)
/health       - Backwards-compat alias for /health/ready
"""
import logging
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)
router = APIRouter()

_DATA_FILES = {
    "crm": Path("data/customers.json"),
    "support": Path("data/support_tickets.json"),
    "analytics": Path("data/analytics.json"),
}


def _check_whisper() -> str:
    try:
        from app.routers.voice import stt  # singleton loaded at startup
        return "ready" if stt is not None else "unavailable"
    except Exception:
        return "unavailable"


def _check_ollama() -> str:
    try:
        import ollama
        ollama.list()
        return "ready"
    except Exception:
        return "unavailable"


def _check_tts() -> str:
    try:
        import edge_tts  # noqa: F401
        return "ready"
    except Exception:
        return "unavailable"


def _check_data_files() -> Dict[str, str]:
    results = {}
    for name, path in _DATA_FILES.items():
        results[name] = "ready" if path.exists() and path.stat().st_size > 0 else "unavailable"
    return results


@router.get("/health/live")
def liveness():
    """Process liveness — lightweight, no dependency checks."""
    return {"status": "alive"}




@router.get("/health/ready")
def readiness(response: Response = None):
    """
    Readiness check — verifies each component can handle requests.

    Status values:
      ready       - all critical components available
      degraded    - some optional components unavailable
      unavailable - critical components missing
    """
    components: Dict[str, str] = {}

    components["whisper"] = _check_whisper()
    components["ollama"] = _check_ollama()
    components["tts"] = _check_tts()

    data_statuses = _check_data_files()
    components.update(data_statuses)

    # Critical components: whisper, ollama, and all data files
    critical = ["whisper", "ollama", "crm", "support", "analytics"]
    critical_failed = [k for k in critical if components.get(k) != "ready"]
    optional_failed = [k for k in components if k not in critical and components[k] != "ready"]

    if critical_failed:
        overall = "unavailable"
    elif optional_failed:
        overall = "degraded"
    else:
        overall = "ready"

    if response is not None:
        response.status_code = 200 if overall in ("ready", "degraded") else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall,
        "components": components,
    }


@router.get("/health")
def health_check(response: Response = None):
    """Backwards-compatible alias for /health/ready."""
    return readiness(response)
