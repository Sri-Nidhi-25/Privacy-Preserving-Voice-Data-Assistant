"""
app/routers/voice.py - Voice query router with observability, failure handling,
and guaranteed resource cleanup.
"""
import asyncio
import logging
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import soundfile as sf
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, BackgroundTasks

from app.config import settings
from app.failure import FailureType, PipelineError
from app.models.voice import QueryResponse
from app.services.llm_orchestrator import LLMOrchestrator
from app.utils.logging import log_event
from app.utils.security import validate_api_key
from app.voice.audio_validation import validate_and_load
from app.voice.obfuscator import FormantPreservingObfuscator
from app.voice.stt import STTEngine
from app.voice.tts import TTSEngine

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/webm",
    "audio/ogg",
}
MAX_FILE_SIZE = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
AUDIO_DIR = Path("temp_audio")
AUDIO_DIR.mkdir(exist_ok=True)

STRENGTH_TO_SEMITONES = {"mild": 2.0, "medium": 4.0, "strong": 6.0}

# Singletons
obfuscator = FormantPreservingObfuscator(
    semitone_shift=STRENGTH_TO_SEMITONES.get(settings.OBFUSCATION_STRENGTH, 2.0),
    jitter=0.5 if settings.OBFUSCATION_STRENGTH == "mild" else 1.0,
)
stt = STTEngine(model_name=settings.STT_MODEL)
tts = TTSEngine(voice=settings.EDGE_TTS_VOICE)
orchestrator = LLMOrchestrator(model=settings.OLLAMA_MODEL)


def _clean_stale_temp_files(max_age_seconds: float = 300.0) -> None:
    """Removes temp audio files older than max_age_seconds (default 5 min)."""
    now = time.time()
    try:
        for p in AUDIO_DIR.glob("*"):
            if p.is_file() and (now - p.stat().st_mtime) > max_age_seconds:
                p.unlink(missing_ok=True)
    except Exception:
        pass


async def _synthesize_and_verify(text: str, output_path: Path) -> None:
    """
    Runs TTS with timeout, then confirms the output file exists on disk with content.
    Raises PipelineError on failure.
    """
    try:
        await asyncio.wait_for(
            tts.synthesize(text, output_path),
            timeout=settings.TTS_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise PipelineError(
            FailureType.TIMEOUT,
            f"TTS synthesis timed out after {settings.TTS_TIMEOUT_SECONDS}s.",
            status_code=504,
        )
    except Exception as exc:
        raise PipelineError(
            FailureType.TTS_FAILED,
            f"TTS synthesis failed: {exc}",
            status_code=500,
        )

    for _ in range(10):
        if output_path.exists() and output_path.stat().st_size > 0:
            return
        await asyncio.sleep(0.1)

    raise PipelineError(
        FailureType.TTS_FAILED,
        f"TTS output file not found or empty after synthesis: {output_path.name}",
        status_code=500,
    )


@router.post("/voice/query", response_model=QueryResponse)
async def voice_query(
    audio_file: UploadFile = File(...),
    api_key: str = Header(...),
    enable_abstention: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    request_id = str(uuid.uuid4())
    t_start = time.perf_counter()
    latency_ms: dict[str, int] = {}
    created_files: list[Path] = []
    request_succeeded = False

    # Stale file cleanup in background
    background_tasks.add_task(_clean_stale_temp_files)

    log_event(logger, request_id, "request", "received", content_type=audio_file.content_type)

    if not validate_api_key(api_key):
        log_event(logger, request_id, "security", "unauthorized")
        raise HTTPException(status_code=401, detail="Invalid API key")

    if audio_file.content_type not in ALLOWED_CONTENT_TYPES:
        log_event(logger, request_id, "validation", "invalid_content_type", content_type=audio_file.content_type)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {audio_file.content_type}. Allowed: WAV, MP3, WebM, OGG",
        )

    suffix_map = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
    }
    suffix = suffix_map.get(audio_file.content_type, ".wav")

    try:
        # 1. Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=AUDIO_DIR) as tmp:
            shutil.copyfileobj(audio_file.file, tmp)
            file_size = tmp.tell()
            input_path = Path(tmp.name)
            created_files.append(input_path)

        # 2. Audio validation layer (size, format, decodability, duration)
        t_val_start = time.perf_counter()
        try:
            y, sr, duration = validate_and_load(input_path, file_size)
        except PipelineError as pe:
            log_event(logger, request_id, "validation", pe.failure_type.value, error=pe.message)
            raise pe.to_http()

        latency_ms["validation"] = int((time.perf_counter() - t_val_start) * 1000)
        log_event(logger, request_id, "validation", "passed", duration_seconds=round(duration, 2), latency_ms=latency_ms["validation"])

        # Write normalized 16kHz mono WAV for downstream vocoder
        normalized_path = input_path.with_suffix(".input.wav")
        sf.write(str(normalized_path), y, sr)
        created_files.append(normalized_path)

        # 3. Voice Obfuscation
        t_obf_start = time.perf_counter()
        obf_path = input_path.with_suffix(".obf.wav")
        created_files.append(obf_path)
        try:
            obfuscator.obfuscate(normalized_path, obf_path)
        except Exception as exc:
            log_event(logger, request_id, "obfuscation", "failed", error=str(exc))
            raise PipelineError(FailureType.OBFUSCATION_FAILED, f"Voice obfuscation failed: {exc}", status_code=500).to_http()

        latency_ms["obfuscation"] = int((time.perf_counter() - t_obf_start) * 1000)
        log_event(logger, request_id, "obfuscation", "completed", latency_ms=latency_ms["obfuscation"])

        # 4. Speech-to-Text (Whisper)
        t_stt_start = time.perf_counter()
        try:
            user_text, stt_confidence = stt.transcribe_with_confidence(obf_path)
        except Exception as exc:
            log_event(logger, request_id, "stt", "failed", error=str(exc))
            raise PipelineError(FailureType.STT_FAILED, f"Speech-to-text failed: {exc}", status_code=500).to_http()

        latency_ms["stt"] = int((time.perf_counter() - t_stt_start) * 1000)
        stt_log_kwargs = {
            "latency_ms": latency_ms["stt"],
            "avg_logprob": stt_confidence.get("avg_logprob"),
            "low_confidence": stt_confidence.get("low_confidence"),
        }
        if settings.LOG_TRANSCRIPTS:
            stt_log_kwargs["transcript"] = user_text
        log_event(logger, request_id, "stt", "completed", **stt_log_kwargs)

        # Low-confidence STT invariant: abstain, never execute data tools
        if stt_confidence["low_confidence"]:
            log_event(logger, request_id, "stt", "low_confidence_abstain")
            answer_text = "Sorry, I didn't catch that clearly. Could you try again?"
            answer_path = input_path.with_suffix(".answer.mp3")
            created_files.append(answer_path)

            try:
                await _synthesize_and_verify(answer_text, answer_path)
                answer_url = f"/static/{answer_path.name}"
            except Exception as tts_err:
                log_event(logger, request_id, "tts", "fallback_failed", error=str(tts_err))
                answer_url = ""

            latency_ms["total"] = int((time.perf_counter() - t_start) * 1000)
            request_succeeded = True
            return QueryResponse(
                obfuscated_audio_url=f"/static/{obf_path.name}",
                answer_audio_url=answer_url,
                transcript=user_text,
                answer_text=answer_text,
                metadata={
                    "request_id": request_id,
                    "data_sources_used": [],
                    "result_count": 0,
                    "freshness": "unknown",
                    "retrieved_at": "",
                    "source_last_updated": "unknown",
                    "tool_calls": [],
                    "low_confidence_transcription": True,
                    "stt_confidence": stt_confidence,
                    "latency_ms": latency_ms,
                    "fallback_used": True,
                },
            )

        # 5. LLM Orchestration & Tool Execution
        t_orch_start = time.perf_counter()
        orchestrator_result = orchestrator.process_query(user_text, enable_abstention=enable_abstention)
        latency_ms["orchestrator"] = int((time.perf_counter() - t_orch_start) * 1000)
        answer_text = orchestrator_result["answer"]
        metadata = orchestrator_result["metadata"]

        # Merge sub-stage latencies into latency_ms
        if "correction_latency_ms" in metadata:
            latency_ms["correction"] = metadata["correction_latency_ms"]
        if "routing_latency_ms" in metadata:
            latency_ms["routing"] = metadata["routing_latency_ms"]
        if "abstention_latency_ms" in metadata:
            latency_ms["abstention"] = metadata["abstention_latency_ms"]
        if "tool_latency_ms" in metadata:
            latency_ms["tool"] = metadata["tool_latency_ms"]

        log_event(
            logger,
            request_id,
            "orchestrator",
            "completed",
            latency_ms=latency_ms["orchestrator"],
            data_sources=metadata.get("data_sources_used", []),
            result_count=metadata.get("result_count", 0),
        )

        # 6. Text-to-Speech (TTS)
        t_tts_start = time.perf_counter()
        answer_path = input_path.with_suffix(".answer.mp3")
        created_files.append(answer_path)
        answer_url = ""

        try:
            await _synthesize_and_verify(answer_text, answer_path)
            answer_url = f"/static/{answer_path.name}"
            metadata["tts_failed"] = False
        except Exception as tts_exc:
            # Controlled failure: preserve text answer even if TTS fails
            log_event(logger, request_id, "tts", "failed_preserving_text", error=str(tts_exc))
            metadata["tts_failed"] = True
            metadata["tts_error"] = str(tts_exc)
            metadata["fallback_used"] = True

        latency_ms["tts"] = int((time.perf_counter() - t_tts_start) * 1000)
        latency_ms["total"] = int((time.perf_counter() - t_start) * 1000)

        metadata["request_id"] = request_id
        metadata["low_confidence_transcription"] = False
        metadata["stt_confidence"] = stt_confidence
        metadata["latency_ms"] = latency_ms

        log_event(logger, request_id, "request", "completed", total_latency_ms=latency_ms["total"])
        request_succeeded = True

        return QueryResponse(
            obfuscated_audio_url=f"/static/{obf_path.name}",
            answer_audio_url=answer_url,
            transcript=user_text,
            answer_text=answer_text,
            metadata=metadata,
        )

    finally:
        # Guaranteed cleanup of raw uploaded audio and intermediate normalized WAV
        # This protects privacy on BOTH success and failure paths
        if "input_path" in locals():
            input_path.unlink(missing_ok=True)
        if "normalized_path" in locals():
            normalized_path.unlink(missing_ok=True)

        # On unhandled error/failure, clean up ALL artifacts immediately
        if not request_succeeded:
            for f in created_files:
                f.unlink(missing_ok=True)
