"""
evaluation/provenance.py - Reproducibility metadata for every evaluation run.
"""
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict


def get_git_commit() -> str:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL
        ).decode().strip()
        return f"{commit}{'_dirty' if dirty else ''}"
    except Exception:
        return "unknown"


def get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def make_run_id() -> str:
    return str(uuid.uuid4())[:8]


def run_metadata(
    *,
    run_id: str,
    dataset_id: str,
    dataset_version: str,
    stt_model: str,
    llm_model: str,
    obfuscation_method: str,
    obfuscation_strength: str,
    seed: int,
    eval_version: str,
    extra: Dict = None,
) -> Dict:
    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "python_version": get_python_version(),
        "os": platform.system(),
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "stt_model": stt_model,
        "llm_model": llm_model,
        "obfuscation_method": obfuscation_method,
        "obfuscation_strength": obfuscation_strength,
        "seed": seed,
        "eval_version": eval_version,
        **(extra or {}),
    }
