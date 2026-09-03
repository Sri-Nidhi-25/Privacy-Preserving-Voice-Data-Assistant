# from pathlib import Path
# from typing import Any, Dict, Tuple
# import numpy as np
# import librosa
# import whisper


# class STTEngine:
#     def __init__(self, model_name: str = "base"):
#         self.model: Any = whisper.load_model(model_name)

#     def transcribe(self, audio_path: Path) -> str:
#         """Backwards-compatible: text only, no confidence info."""
#         text, _ = self.transcribe_with_confidence(audio_path)
#         return text

#     def transcribe_with_confidence(self, audio_path: Path) -> Tuple[str, Dict[str, Any]]:
#         # Load audio via librosa and pass as a numpy array.
#         #
#         # Whisper accepts both a file-path string and a float32 numpy array.
#         # When given a path string it invokes FFmpeg internally to decode the
#         # file -- if FFmpeg is not installed (or not on PATH) that call fails
#         # with FileNotFoundError even for files Whisper could otherwise handle.
#         # Loading with librosa first side-steps that dependency entirely:
#         # librosa uses soundfile (libsndfile) for WAV/FLAC and mpg123 for MP3,
#         # neither of which requires FFmpeg.  Whisper expects float32 at 16 kHz
#         # mono, which is exactly what librosa.load(..., sr=16000, mono=True)
#         # returns.
#         audio_np: np.ndarray = librosa.load(str(audio_path), sr=16000, mono=True)[0]

#         result = self.model.transcribe(
#             audio_np,
#             language="en",
#             condition_on_previous_text=False,
#             # Tuple, not a single float: Whisper's own decoding loop retries
#             # a segment at increasingly higher temperatures whenever
#             # compression_ratio / avg_logprob / no_speech_prob look bad --
#             # this is the built-in defense against "confident hallucination"
#             # on noisy/distorted audio. A single float disables that retry
#             # loop and locks in whatever the first greedy decode produces.
#             temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
#         )

#         segments = result.get("segments", [])
#         if segments:
#             avg_logprob = sum(s.get("avg_logprob", 0.0) for s in segments) / len(segments)
#             no_speech_prob = max(s.get("no_speech_prob", 0.0) for s in segments)
#             compression_ratio = max(s.get("compression_ratio", 0.0) for s in segments)
#         else:
#             # No segments at all (e.g. total silence) -- treat as maximally
#             # low confidence rather than silently returning empty text.
#             avg_logprob, no_speech_prob, compression_ratio = -999.0, 1.0, 0.0

#         # Same heuristic thresholds Whisper's own fallback logic uses
#         # internally to judge a segment as unreliable.
#         low_confidence = (
#             avg_logprob < -1.0
#             or no_speech_prob > 0.6
#             or compression_ratio > 2.4
#         )

#         confidence = {
#             "avg_logprob": round(avg_logprob, 3),
#             "no_speech_prob": round(no_speech_prob, 3),
#             "compression_ratio": round(compression_ratio, 3),
#             "low_confidence": low_confidence,
#         }

#         return str(result["text"]).strip(), confidence

from pathlib import Path
from typing import Any, Dict, Tuple
import librosa
import whisper


class STTEngine:
    def __init__(self, model_name: str = "base"):
        self.model: Any = whisper.load_model(model_name)

    def transcribe(self, audio_path: Path) -> str:
        """Backwards-compatible: text only, no confidence info."""
        text, _ = self.transcribe_with_confidence(audio_path)
        return text

    def transcribe_with_confidence(self, audio_path: Path) -> Tuple[str, Dict[str, Any]]:
        # Load as a float32 numpy array at 16kHz (Whisper's native format)
        # and pass the array directly rather than a path string. Whisper's
        # transcribe() calls out to FFmpeg internally to decode a path, so
        # any environment without FFmpeg on PATH fails on non-WAV input.
        # librosa.load handles the decode itself (via soundfile/audioread),
        # so this removes the FFmpeg dependency entirely.
        audio_np, _ = librosa.load(str(audio_path), sr=16000, mono=True)

        result = self.model.transcribe(
            audio_np,
            language="en",
            condition_on_previous_text=False,
            # Tuple, not a single float: Whisper's own decoding loop retries
            # a segment at increasingly higher temperatures whenever
            # compression_ratio / avg_logprob / no_speech_prob look bad --
            # this is the built-in defense against "confident hallucination"
            # on noisy/distorted audio. A single float disables that retry
            # loop and locks in whatever the first greedy decode produces.
            temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        )

        segments = result.get("segments", [])
        if segments:
            avg_logprob = sum(s.get("avg_logprob", 0.0) for s in segments) / len(segments)
            no_speech_prob = max(s.get("no_speech_prob", 0.0) for s in segments)
            compression_ratio = max(s.get("compression_ratio", 0.0) for s in segments)
        else:
            # No segments at all (e.g. total silence) -- treat as maximally
            # low confidence rather than silently returning empty text.
            avg_logprob, no_speech_prob, compression_ratio = -999.0, 1.0, 0.0

        # Same heuristic thresholds Whisper's own fallback logic uses
        # internally to judge a segment as unreliable.
        low_confidence = (
            avg_logprob < -1.0
            or no_speech_prob > 0.6
            or compression_ratio > 2.4
        )

        confidence = {
            "avg_logprob": round(avg_logprob, 3),
            "no_speech_prob": round(no_speech_prob, 3),
            "compression_ratio": round(compression_ratio, 3),
            "low_confidence": low_confidence,
        }

        return str(result["text"]).strip(), confidence