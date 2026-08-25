# import shutil
# import tempfile
# from pathlib import Path

# from fastapi import APIRouter, UploadFile, File, Header, HTTPException

# from app.config import settings
# from app.models.voice import QueryResponse
# from app.services.llm_orchestrator import LLMOrchestrator
# from app.utils.security import validate_api_key
# from app.voice.obfuscator import VoiceObfuscator
# from app.voice.stt import STTEngine
# from app.voice.tts import TTSEngine

# router = APIRouter()

# ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/webm", "audio/ogg"}
# MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
# AUDIO_DIR = Path("temp_audio")
# AUDIO_DIR.mkdir(exist_ok=True)

# # Singletons
# obfuscator = VoiceObfuscator(strength=settings.OBFUSCATION_STRENGTH)
# stt = STTEngine(model_name=settings.STT_MODEL)
# tts = TTSEngine(voice=settings.EDGE_TTS_VOICE)
# orchestrator = LLMOrchestrator(model=settings.OLLAMA_MODEL)


# @router.post("/voice/query", response_model=QueryResponse)
# async def voice_query(audio_file: UploadFile = File(...), api_key: str = Header(...)):
#     if not validate_api_key(api_key):
#         raise HTTPException(status_code=401, detail="Invalid API key")

#     if audio_file.content_type not in ALLOWED_CONTENT_TYPES:
#         raise HTTPException(status_code=400, detail="Only WAV or MP3 allowed")

#     suffix_map = {"audio/wav": ".wav", "audio/mpeg": ".mp3", "audio/webm": ".webm", "audio/ogg": ".ogg"}
#     suffix = suffix_map.get(audio_file.content_type, ".wav")

#     with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=AUDIO_DIR) as tmp:
#         shutil.copyfileobj(audio_file.file, tmp)
#         if tmp.tell() > MAX_FILE_SIZE:
#             raise HTTPException(status_code=400, detail="File too large (max 25MB)")
#         input_path = Path(tmp.name)

#     obf_path = input_path.with_suffix(".obf.wav")
#     obfuscator.obfuscate(input_path, obf_path)

#     user_text, stt_confidence = stt.transcribe_with_confidence(obf_path)

#     # If Whisper itself flags this segment as unreliable (likely
#     # hallucinated / no real speech detected), don't hand it to the
#     # correction step or the orchestrator -- correction can fix a garbled
#     # word, but it can't recover a transcript that was fabricated from
#     # noise, and running it through anyway just produces a confidently
#     # wrong answer with no visible sign anything went wrong.
#     if stt_confidence["low_confidence"]:
#         answer_text = "Sorry, I didn't catch that clearly. Could you try again?"
#         answer_path = input_path.with_suffix(".answer.mp3")
#         await tts.synthesize(answer_text, answer_path)

#         return QueryResponse(
#             obfuscated_audio_url=f"/static/{obf_path.name}",
#             answer_audio_url=f"/static/{answer_path.name}",
#             transcript=user_text,
#             answer_text=answer_text,
#             metadata={
#                 "data_sources_used": [],
#                 "result_count": 0,
#                 "freshness": "unknown",
#                 "tool_calls": [],
#                 "low_confidence_transcription": True,
#                 "stt_confidence": stt_confidence,
#             },
#         )

#     orchestrator_result = orchestrator.process_query(user_text)
#     answer_text = orchestrator_result["answer"]

#     answer_path = input_path.with_suffix(".answer.mp3")
#     await tts.synthesize(answer_text, answer_path)

#     metadata = orchestrator_result["metadata"]
#     metadata["low_confidence_transcription"] = False
#     metadata["stt_confidence"] = stt_confidence

#     return QueryResponse(
#         obfuscated_audio_url=f"/static/{obf_path.name}",
#         answer_audio_url=f"/static/{answer_path.name}",
#         transcript=user_text,
#         answer_text=answer_text,
#         metadata=metadata,
#     )

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Header, HTTPException

from app.config import settings
from app.models.voice import QueryResponse
from app.services.llm_orchestrator import LLMOrchestrator
from app.utils.security import validate_api_key
from app.voice.obfuscator import VoiceObfuscator
from app.voice.stt import STTEngine
from app.voice.tts import TTSEngine

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/webm", "audio/ogg"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
AUDIO_DIR = Path("temp_audio")
AUDIO_DIR.mkdir(exist_ok=True)

# Singletons
obfuscator = VoiceObfuscator(strength=settings.OBFUSCATION_STRENGTH)
stt = STTEngine(model_name=settings.STT_MODEL)
tts = TTSEngine(voice=settings.EDGE_TTS_VOICE)
orchestrator = LLMOrchestrator(model=settings.OLLAMA_MODEL)


@router.post("/voice/query", response_model=QueryResponse)
async def voice_query(audio_file: UploadFile = File(...), api_key: str = Header(...)):
    if not validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    if audio_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only WAV or MP3 allowed")

    suffix_map = {"audio/wav": ".wav", "audio/mpeg": ".mp3", "audio/webm": ".webm", "audio/ogg": ".ogg"}
    suffix = suffix_map.get(audio_file.content_type, ".wav")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=AUDIO_DIR) as tmp:
        shutil.copyfileobj(audio_file.file, tmp)
        if tmp.tell() > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 25MB)")
        input_path = Path(tmp.name)

    obf_path = input_path.with_suffix(".obf.wav")
    obfuscator.obfuscate(input_path, obf_path)

    user_text, stt_confidence = stt.transcribe_with_confidence(obf_path)

    # If Whisper itself flags this segment as unreliable (likely
    # hallucinated / no real speech detected), don't hand it to the
    # correction step or the orchestrator -- correction can fix a garbled
    # word, but it can't recover a transcript that was fabricated from
    # noise, and running it through anyway just produces a confidently
    # wrong answer with no visible sign anything went wrong.
    if stt_confidence["low_confidence"]:
        answer_text = "Sorry, I didn't catch that clearly. Could you try again?"
        answer_path = input_path.with_suffix(".answer.mp3")
        await tts.synthesize(answer_text, answer_path)

        return QueryResponse(
            obfuscated_audio_url=f"/static/{obf_path.name}",
            answer_audio_url=f"/static/{answer_path.name}",
            transcript=user_text,
            answer_text=answer_text,
            metadata={
                "data_sources_used": [],
                "result_count": 0,
                "freshness": "unknown",
                "tool_calls": [],
                "low_confidence_transcription": True,
                "stt_confidence": stt_confidence,
            },
        )

    orchestrator_result = orchestrator.process_query(user_text)
    answer_text = orchestrator_result["answer"]

    answer_path = input_path.with_suffix(".answer.mp3")
    await tts.synthesize(answer_text, answer_path)

    metadata = orchestrator_result["metadata"]
    metadata["low_confidence_transcription"] = False
    metadata["stt_confidence"] = stt_confidence

    return QueryResponse(
        obfuscated_audio_url=f"/static/{obf_path.name}",
        answer_audio_url=f"/static/{answer_path.name}",
        transcript=user_text,
        answer_text=answer_text,
        metadata=metadata,
    )