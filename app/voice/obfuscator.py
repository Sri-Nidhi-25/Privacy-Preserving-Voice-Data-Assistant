# # import random
# # from pathlib import Path
# # import librosa
# # import soundfile as sf

# # class VoiceObfuscator:
# #     SHIFT_RANGES = {"mild": (-1, 1 ), "medium": (-4, 4), "strong": (-6, 6)}

# #     def __init__(self, strength: str = "mild"):
# #         self.shift_range = self.SHIFT_RANGES.get(strength, (-1, 1 ))

# #     def obfuscate(self, input_path: Path, output_path: Path) -> None:
# #         y, sr = librosa.load(input_path, sr=16000)

# #         semitones = random.uniform(*self.shift_range)
# #         y = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)

# #         rate = random.uniform(0.98, 1.02)
# #         y = librosa.effects.time_stretch(y, rate=rate)

# #         sf.write(output_path, y, sr)

# import random
# from pathlib import Path

# import numpy as np
# import librosa
# import pyworld as pw
# import soundfile as sf


# class VoiceObfuscator:
#     SHIFT_RANGES = {"mild": (-1, 1), "medium": (-4, 4), "strong": (-6, 6)}

#     def __init__(self, strength: str = "mild"):
#         self.shift_range = self.SHIFT_RANGES.get(strength, (-1, 1))

#     def obfuscate(self, input_path: Path, output_path: Path) -> None:
#         y, sr = librosa.load(input_path, sr=16000)

#         semitones = random.uniform(*self.shift_range)
#         y = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)

#         rate = random.uniform(0.98, 1.02)
#         y = librosa.effects.time_stretch(y, rate=rate)

#         sf.write(output_path, y, sr)


# class FormantPreservingObfuscator:
#     """
#     Shifts F0 (pitch) while holding the spectral envelope (formants) fixed,
#     using the WORLD vocoder.

#     Why: a naive pitch_shift (librosa's phase vocoder, as used in
#     VoiceObfuscator above) moves F0 *and* smears the spectral envelope, and
#     the spectral envelope is what carries the phonetic content ASR models
#     key off of -- so naive shifts buy speaker obfuscation at the direct
#     expense of transcription accuracy.

#     WORLD decomposes speech into three independently-editable components:
#       - f0:  fundamental frequency contour (pitch)
#       - sp:  spectral envelope (formants -- vocal tract resonance shape,
#              carries most of both phonetic content AND speaker timbre)
#       - ap:  aperiodicity (breathiness / noise component)

#     Here we only touch f0 and resynthesize sp/ap untouched. Net effect vs.
#     VoiceObfuscator.obfuscate(): weaker speaker-identity disturbance (since
#     formants -- the stronger speaker cue -- are left alone), but much
#     smaller transcription accuracy cost, since ASR cares more about the
#     spectral envelope than about absolute F0.

#     This is a genuinely different tradeoff point, not a strictly-better
#     replacement -- pick based on which side of the privacy/accuracy line
#     matters more for a given deployment.
#     """

#     def __init__(self, semitone_shift: float = 4.0, randomize: bool = True, jitter: float = 1.5):
#         """
#         semitone_shift: base pitch shift in semitones. Sign matters
#                          (negative = lower, positive = higher).
#         randomize:       if True, add random per-call jitter on top of
#                          semitone_shift so the same speaker doesn't produce
#                          a fixed, re-identifiable offset every time.
#         jitter:          +/- range in semitones for the randomization.
#         """
#         self.semitone_shift = semitone_shift
#         self.randomize = randomize
#         self.jitter = jitter

#     def obfuscate(self, input_path: Path, output_path: Path) -> None:
#         x, fs = sf.read(str(input_path))
#         if x.ndim > 1:
#             x = x.mean(axis=1)  # downmix to mono if needed
#         x = np.ascontiguousarray(x, dtype=np.float64)

#         # --- Analysis: decompose into pitch / spectral envelope / aperiodicity ---
#         f0, t = getattr(pw, "dio")(x, fs)
#         f0 = getattr(pw, "stonemask")(x, f0, t, fs)
#         sp = getattr(pw, "cheaptrick")(x, f0, t, fs)
#         ap = getattr(pw, "d4c")(x, f0, t, fs)     # aperiodicity -- untouched

#         # --- Modify only F0 ---
#         shift = self.semitone_shift
#         if self.randomize:
#             shift += random.uniform(-self.jitter, self.jitter)
#         ratio = 2 ** (shift / 12.0)

#         # f0 == 0 marks unvoiced frames; leave those at 0, don't scale silence/noise
#         f0_shifted = np.where(f0 > 0, f0 * ratio, f0)

#         # --- Resynthesis with original formant structure ---
#         y = getattr(pw, "synthesize")(f0_shifted, sp, ap, fs)  # type: ignore[attr-defined]
#         sf.write(str(output_path), y, fs)


import random
from pathlib import Path
import librosa
import soundfile as sf


class VoiceObfuscator:
    SHIFT_RANGES = {"mild": (-1, 1), "medium": (-4, 4), "strong": (-6, 6)}

    # Tempo alone buys very little speaker obfuscation (a 2-4% rate change
    # is barely perceptible), so it isn't scaled by "strength" -- it's just
    # a second, cheap source of per-call variance when it's the one chosen.
    RATE_RANGE = (0.96, 1.04)

    # Weighted toward pitch since that's the transform actually doing
    # privacy work; tempo is included mainly so the obfuscation isn't
    # perfectly predictable/fingerprintable across calls.
    MODE_WEIGHTS = {"pitch": 0.75, "tempo": 0.25}

    def __init__(self, strength: str = "mild"):
        self.shift_range = self.SHIFT_RANGES.get(strength, (-1, 1))

    def obfuscate(self, input_path: Path, output_path: Path) -> None:
        y, sr = librosa.load(input_path, sr=16000)

        # Apply exactly ONE perturbation per call rather than stacking both.
        #
        # librosa.effects.pitch_shift is itself implemented as a phase-
        # vocoder time-stretch + resample internally. Following it with an
        # explicit time_stretch() runs the audio through a SECOND,
        # independent phase-vocoder pass -- each pass has its own phase-
        # estimation error, and those errors compound rather than average
        # out. That's real signal degradation for very little extra privacy
        # benefit, since tempo change alone barely disturbs speaker identity.
        mode = random.choices(
            population=list(self.MODE_WEIGHTS.keys()),
            weights=list(self.MODE_WEIGHTS.values()),
            k=1,
        )[0]

        if mode == "pitch":
            semitones = random.uniform(*self.shift_range)
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
        else:
            rate = random.uniform(*self.RATE_RANGE)
            y = librosa.effects.time_stretch(y, rate=rate)

        sf.write(output_path, y, sr)