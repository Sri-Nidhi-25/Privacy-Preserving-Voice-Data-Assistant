import random
from pathlib import Path
import librosa
import soundfile as sf

class VoiceObfuscator:
    SHIFT_RANGES = {"mild": (-2, 2), "medium": (-4, 4), "strong": (-6, 6)}

    def __init__(self, strength: str = "mild"):
        self.shift_range = self.SHIFT_RANGES.get(strength, (-2, 2))

    def obfuscate(self, input_path: Path, output_path: Path) -> None:
        y, sr = librosa.load(input_path, sr=16000)

        semitones = random.uniform(*self.shift_range)
        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)

        rate = random.uniform(0.98, 1.02)
        y = librosa.effects.time_stretch(y, rate=rate)

        sf.write(output_path, y, sr)


