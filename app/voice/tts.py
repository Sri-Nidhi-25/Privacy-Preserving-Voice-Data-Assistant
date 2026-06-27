from pathlib import Path
import edge_tts


class TTSEngine:
    def __init__(self, voice: str = "en-US-AriaNeural"):
        self.voice = voice

    async def synthesize(self, text: str, output_path: Path) -> None:
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_path))