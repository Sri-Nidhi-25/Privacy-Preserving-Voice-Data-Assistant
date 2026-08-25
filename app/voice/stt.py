# from pathlib import Path
# from typing import Any
# import whisper


# class STTEngine:
#     def __init__(self, model_name: str = "base"):
#         self.model: Any = whisper.load_model(model_name)

#     # def transcribe(self, audio_path: Path) -> str:
#     #     result = self.model.transcribe(str(audio_path), language="en", condition_on_previous_text=False)
#     #     return str(result["text"]).strip()

#     def transcribe(self, audio_path: Path) -> str:
#         result = self.model.transcribe(
#             str(audio_path),
#             language="en",
#             condition_on_previous_text=False,
#             temperature=0,
#         )
#         return str(result["text"]).strip()


from pathlib import Path
from typing import Any, Dict, Tuple
import whisper


class STTEngine:
    def __init__(self, model_name: str = "base"):
        self.model: Any = whisper.load_model(model_name)

    def transcribe(self, audio_path: Path) -> str:
        """Backwards-compatible: text only, no confidence info."""
        text, _ = self.transcribe_with_confidence(audio_path)
        return text

    def transcribe_with_confidence(self, audio_path: Path) -> Tuple[str, Dict[str, Any]]:
        result = self.model.transcribe(
            str(audio_path),
            language="en",
            condition_on_previous_text=False,
            # IMPORTANT: this must be a tuple, not a single float.
            #
            # Whisper's own decoding loop retries a segment at increasingly
            # higher temperatures whenever compression_ratio / avg_logprob /
            # no_speech_prob look bad -- this is the built-in defense
            # against exactly the "confident hallucination" failure mode
            # (fluent but fabricated text on noisy/distorted audio). Passing
            # a single float (e.g. temperature=0) disables that retry loop
            # entirely and locks in whatever the first greedy decode
            # produces, good or bad. This was previously pinned to 0, which
            # is almost certainly why obfuscated audio was producing wildly
            # inconsistent, occasionally fabricated transcripts.
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