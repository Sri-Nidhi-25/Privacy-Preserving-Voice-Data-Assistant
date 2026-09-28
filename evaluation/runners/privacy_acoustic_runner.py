"""
evaluation/runners/privacy_acoustic_runner.py - Physical Acoustic Obfuscation & Pitch Shift Analysis.

Measures physical acoustic transformations between original speech and obfuscated variants
using objective acoustic feature extraction (F0 fundamental frequency, pitch shift,
voiced frame statistics, and spectral envelope).

IMPORTANT SCIENTIFIC CAVEAT:
Speaker privacy was NOT empirically established in this study.
F0 fundamental frequency modification measures physical pitch transformation, not biometric
speaker anonymity against neural verification models (e.g. ECAPA-TDNN / x-vectors).
FormantPreservingObfuscator explicitly preserves the spectral envelope (formants), which
carries primary speaker identity cues.

Usage:
    python -m evaluation.runners.privacy_acoustic_runner \
        --audio-dir benchmark_audio \
        --output evaluation/results/ \
        --seed 42
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf
import tempfile
import shutil

from app.voice.obfuscator import VoiceObfuscator, FormantPreservingObfuscator
from evaluation.provenance import make_run_id


def extract_f0_profile(y: np.ndarray, sr: int = 16000) -> Dict[str, float]:
    """Extracts continuous F0 trajectory and summary statistics using YIN algorithm."""
    try:
        f0 = librosa.yin(y, fmin=60, fmax=380, sr=sr)
        valid = f0[(f0 >= 60) & (f0 <= 380)]
        if len(valid) == 0:
            return {"f0_mean": 0.0, "f0_std": 0.0, "f0_median": 0.0, "f0_iqr": 0.0, "voiced_ratio": 0.0}
        
        q75, q25 = np.percentile(valid, [75, 25])
        return {
            "f0_mean": round(float(np.mean(valid)), 2),
            "f0_std": round(float(np.std(valid)), 2),
            "f0_median": round(float(np.median(valid)), 2),
            "f0_iqr": round(float(q75 - q25), 2),
            "voiced_ratio": round(float(len(valid) / len(f0)), 3),
        }
    except Exception:
        return {"f0_mean": 0.0, "f0_std": 0.0, "f0_median": 0.0, "f0_iqr": 0.0, "voiced_ratio": 0.0}


def run_privacy_acoustic_study(
    audio_dir: Path,
    output_dir: Path,
    seed: int = 42,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = make_run_id()

    # Find benchmark wav files
    wav_files = list(audio_dir.glob("phrase_*.wav"))
    # Filter for clean raw files (not already obfuscated suffix)
    raw_files = [f for f in wav_files if not any(s in f.name for s in ["_mild", "_medium", "_strong", "_none"])]
    
    if not raw_files:
        # Fallback to any wav files
        raw_files = wav_files[:5]

    print(f"=== Acoustic Privacy & Pitch Distribution Study (run_id={run_id}) ===")
    print(f"Analyzing {len(raw_files)} audio samples across obfuscation configurations")

    obfuscators = {
        "naive_mild": VoiceObfuscator(strength="mild"),
        "naive_medium": VoiceObfuscator(strength="medium"),
        "naive_strong": VoiceObfuscator(strength="strong"),
        "formant_mild": FormantPreservingObfuscator(semitone_shift=2.0, jitter=0.5, randomize=False),
        "formant_medium": FormantPreservingObfuscator(semitone_shift=4.0, jitter=1.0, randomize=False),
        "formant_strong": FormantPreservingObfuscator(semitone_shift=6.0, jitter=1.5, randomize=False),
    }

    results_by_method = {m: [] for m in list(obfuscators.keys()) + ["baseline"]}

    tmp_dir = Path(tempfile.mkdtemp(prefix="privacy_eval_"))

    try:
        for idx, fpath in enumerate(raw_files[:6]):
            try:
                y_base, sr = librosa.load(str(fpath), sr=16000, mono=True)
            except Exception:
                continue

            base_f0 = extract_f0_profile(y_base, sr)
            results_by_method["baseline"].append({
                "file": fpath.name,
                "f0_profile": base_f0,
                "delta_f0_mean": 0.0,
            })

            in_p = tmp_dir / f"in_{idx}.wav"
            out_p = tmp_dir / f"out_{idx}.wav"
            sf.write(str(in_p), y_base, sr)

            for name, obf in obfuscators.items():
                try:
                    obf.obfuscate(in_p, out_p)
                    y_obf, _ = librosa.load(str(out_p), sr=16000, mono=True)
                    obf_f0 = extract_f0_profile(y_obf, sr)
                    delta_f0 = round(abs(obf_f0["f0_mean"] - base_f0["f0_mean"]), 2)

                    results_by_method[name].append({
                        "file": fpath.name,
                        "f0_profile": obf_f0,
                        "delta_f0_mean": delta_f0,
                    })
                except Exception:
                    pass
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Aggregate statistics
    summary_by_method = {}
    for name, items in results_by_method.items():
        if not items:
            continue
        avg_delta = float(np.mean([it["delta_f0_mean"] for it in items]))
        avg_f0_mean = float(np.mean([it["f0_profile"]["f0_mean"] for it in items]))
        avg_f0_std = float(np.mean([it["f0_profile"]["f0_std"] for it in items]))

        summary_by_method[name] = {
            "method": name,
            "samples_analyzed": len(items),
            "average_f0_hz": round(avg_f0_mean, 2),
            "average_f0_std_hz": round(avg_f0_std, 2),
            "average_f0_shift_hz": round(avg_delta, 2),
        }

    print("\n" + "=" * 80)
    print(f"{'Obfuscation Method':<22} | {'Avg F0 (Hz)':<12} | {'F0 Spread (Hz)':<14} | {'Mean Shift (Hz)':<15}")
    print("-" * 80)
    for name, s in summary_by_method.items():
        print(f"{name:<22} | {s['average_f0_hz']:<12.1f} | {s['average_f0_std_hz']:<14.1f} | {s['average_f0_shift_hz']:<15.1f}")
    print("=" * 80)

    out_file = output_dir / f"privacy_acoustic_profile_{run_id}.json"
    report_data = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary_by_method,
        "details": results_by_method,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"Acoustic profile saved to {out_file}\n")
    return report_data


def main():
    parser = argparse.ArgumentParser(description="Empirical Acoustic Privacy Profile Runner")
    parser.add_argument("--audio-dir", type=Path, default=Path("benchmark_audio"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run_privacy_acoustic_study(
        audio_dir=args.audio_dir,
        output_dir=args.output,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
