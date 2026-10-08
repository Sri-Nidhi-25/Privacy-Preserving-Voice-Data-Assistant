"""Integrity tests for Phase 5 datasets and frozen Phase 4.6 baselines."""

import json
import hashlib
from pathlib import Path
import pytest

DATASETS_DIR = Path("evaluation/datasets")
PHASE5_DIR = DATASETS_DIR / "phase5"

# Frozen Phase 4.6 SHA256 hashes — computed from the audited, locked files.
FROZEN_HASHES = {
    "held_out_test_v1.jsonl": "82efa536759a51819176d576aa168ad12c03be7ac0db3487985457791c9924f7",
    "challenge_v1.jsonl": "0ded94acbe7bd6e3c050990b3073d989e3ab0b30678c92a2b4b59dd727e0ab66",
}


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_frozen_baselines_integrity():
    """Verify frozen Phase 4.6 baseline datasets remain strictly unmodified."""
    held_out = DATASETS_DIR / "held_out_test" / "held_out_test_v1.jsonl"
    challenge = DATASETS_DIR / "challenge" / "challenge_v1.jsonl"

    assert held_out.exists(), "Held-out test dataset missing"
    assert challenge.exists(), "Challenge test dataset missing"

    assert compute_sha256(held_out) == FROZEN_HASHES["held_out_test_v1.jsonl"], (
        "CRITICAL: Frozen held_out_test_v1.jsonl hash mismatch! Dataset was contaminated."
    )
    assert compute_sha256(challenge) == FROZEN_HASHES["challenge_v1.jsonl"], (
        "CRITICAL: Frozen challenge_v1.jsonl hash mismatch! Dataset was contaminated."
    )


def test_phase5_dataset_counts_and_schemas():
    """Verify Phase 5 dataset files, sample counts, and JSON schemas."""
    expected_datasets = {
        PHASE5_DIR / "dev" / "dev_phase5.jsonl": 20,
        PHASE5_DIR / "validation" / "val_phase5.jsonl": 20,
        PHASE5_DIR / "distractors" / "distractors_v1.jsonl": 20,
        PHASE5_DIR / "ambiguity" / "ambiguity_v1.jsonl": 15,
        PHASE5_DIR / "adversarial" / "adversarial_v1.jsonl": 15,
        PHASE5_DIR / "ood" / "ood_v1.jsonl": 15,
    }

    for path, expected_count in expected_datasets.items():
        assert path.exists(), f"Phase 5 dataset missing: {path}"
        with open(path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == expected_count, (
            f"Dataset {path.name} count mismatch: got {len(lines)}, expected {expected_count}"
        )
        for row in lines:
            assert "case_id" in row, f"Missing 'case_id' in {path.name}"
            assert "input_text" in row, f"Missing 'input_text' in {path.name}"
            assert "expected_route" in row, f"Missing 'expected_route' in {path.name}"



def test_matched_pairs_schema():
    """Verify matched-pairs dataset structure."""
    pairs_file = PHASE5_DIR / "distractors" / "matched_pairs_v1.jsonl"
    assert pairs_file.exists(), "matched_pairs_v1.jsonl missing"

    with open(pairs_file, "r", encoding="utf-8") as f:
        pairs = [json.loads(l) for l in f if l.strip()]

    assert len(pairs) == 10, f"Expected 10 matched pairs, found {len(pairs)}"
    for p in pairs:
        assert "pair_id" in p, "Missing 'pair_id'"
        assert "domain" in p, "Missing 'domain'"
        assert "operational" in p, "Missing 'operational'"
        assert "distractor" in p, "Missing 'distractor'"
        # operational and distractor are plain text strings (not dicts)
        assert isinstance(p["operational"], str), "'operational' should be a text string"
        assert isinstance(p["distractor"], str), "'distractor' should be a text string"
        # Pairing must involve the same topic
        assert "op_tool" in p, "Missing 'op_tool' (expected tool for the operational side)"
