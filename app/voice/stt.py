from pathlib import Path
from typing import Any
import whisper


class STTEngine:
    def __init__(self, model_name: str = "base"):
        self.model: Any = whisper.load_model(model_name)

    # def transcribe(self, audio_path: Path) -> str:
    #     result = self.model.transcribe(str(audio_path), language="en", condition_on_previous_text=False)
    #     return str(result["text"]).strip()

    def transcribe(self, audio_path: Path) -> str:
        result = self.model.transcribe(
            str(audio_path),
            language="en",
            condition_on_previous_text=False,
            temperature=0,
        )
        return str(result["text"]).strip()
