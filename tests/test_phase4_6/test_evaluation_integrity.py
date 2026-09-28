"""
tests/test_phase4_6/test_evaluation_integrity.py - Evaluation Framework & Experimental Integrity Tests.

Verifies:
1. Dataset Cryptographic Integrity (Frozen hashes strictly enforced).
2. Runner Provenance & Metadata Completeness.
3. Oracle-Free Metamorphic Relation Properties.
4. Ablation Isolation (Each condition alters mechanism; no-op ablations rejected).
5. Claim Integrity (Reported aggregates exactly match raw results).
6. Level A / Level B Evaluation Separation.
"""
import hashlib
import json
from pathlib import Path
import pytest

from app.services.intent_router import classify_intent
from evaluation.run_final_experiment import calculate_sha256, verify_frozen_datasets
from evaluation.runners.ablation_runner import run_ablation_study


MANIFEST_PATH = Path("evaluation/datasets/manifest.json")
RESULTS_DIR = Path("experiments/results")


class TestDatasetIntegrity:
    """Ensures frozen datasets cannot silently change."""

    def test_frozen_dataset_hashes(self):
        assert MANIFEST_PATH.exists(), "Manifest file missing"
        verification = verify_frozen_datasets(MANIFEST_PATH)
        assert len(verification) >= 4
        for tier, data in verification.items():
            assert data["status"] == "VERIFIED_UNCHANGED"
            assert len(data["sha256"]) == 64

    def test_dataset_case_counts(self):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        for tier, spec in manifest["datasets"].items():
            p = Path(spec["path"])
            with open(p, encoding="utf-8-sig") as f:
                cases = [line for line in f if line.strip()]
            assert len(cases) == spec["cases_count"], (
                f"Case count mismatch in {tier}: expected {spec['cases_count']}, got {len(cases)}"
            )


class TestMetamorphicProperties:
    """Verifies that metamorphic transformations are genuinely oracle-free."""

    def test_politeness_transformation_alters_string_not_intent(self):
        query = "Show me active customers"
        transformed = "Please show me active customers"
        assert query != transformed

        res_orig = classify_intent(query)
        res_trans = classify_intent(transformed)
        # Metamorphic invariant: R(f(x), f(T(x))) holds without expected label
        assert res_trans.intent == res_orig.intent
        assert res_trans.route == res_orig.route
        assert res_trans.target_tool == res_orig.target_tool

    def test_casing_transformation_preserves_routing(self):
        query = "Show open tickets"
        upper = query.upper()
        lower = query.lower()

        res_orig = classify_intent(query)
        res_upper = classify_intent(upper)
        res_lower = classify_intent(lower)

        assert res_upper.intent == res_orig.intent
        assert res_lower.intent == res_orig.intent


class TestAblationMechanismIsolation:
    """Verifies that every ablation condition genuinely isolates a mechanism."""

    def test_no_op_ablations_are_rejected(self, tmp_path):
        held_out_path = Path("evaluation/datasets/held_out_test/held_out_test_v1.jsonl")
        summary = run_ablation_study(held_out_path, tmp_path, seed=42)
        results = summary["results"]

        full = results["full_system"]
        ablate_router = results["ablate_intent_router"]
        ablate_corr = results["ablate_correction_guard"]
        ablate_align = results["ablate_tool_alignment"]
        ablate_retry = results["ablate_retry_policy"]

        # 1. Ablate router must differ in routing metrics
        assert ablate_router["adversarial_fpr"] > full["adversarial_fpr"], "Router ablation failed to change FPR"

        # 2. Ablate correction guard must differ in correction safety
        assert ablate_corr["correction_safety_rate"] < full["correction_safety_rate"], "Correction ablation failed to change safety"

        # 3. Ablate tool alignment must differ in alignment accuracy
        assert ablate_align["tool_alignment_accuracy"] < full["tool_alignment_accuracy"], "Tool alignment ablation is a no-op!"

        # 4. Ablate retry policy must fail fault recovery
        assert full["transient_fault_recovered"] is True
        assert ablate_retry["transient_fault_recovered"] is False


class TestClaimAndEvaluationIntegrity:
    """Verifies that reported aggregates match raw records and Level A/B are separated."""

    def test_component_and_pipeline_separation(self):
        comp_file = RESULTS_DIR / "component_results.jsonl"
        pipe_file = RESULTS_DIR / "pipeline_results.jsonl"

        if not comp_file.exists() or not pipe_file.exists():
            pytest.skip("Run master experiment to generate results")

        with open(comp_file, encoding="utf-8") as f:
            comp_records = [json.loads(line) for line in f if line.strip()]
        with open(pipe_file, encoding="utf-8") as f:
            pipe_records = [json.loads(line) for line in f if line.strip()]

        # Level A must be text-based
        for r in comp_records:
            assert r["input_type"] == "text"

        # Level B must be real speech audio
        for r in pipe_records:
            assert r["input_type"] == "real_speech_audio"
            assert "wer" in r
            assert "latency_ms" in r

    def test_aggregate_equals_raw_mean(self):
        comp_file = RESULTS_DIR / "component_results.jsonl"
        metrics_file = RESULTS_DIR / "metrics.json"

        if not comp_file.exists() or not metrics_file.exists():
            pytest.skip("Run master experiment to generate results")

        with open(metrics_file, encoding="utf-8") as f:
            metrics = json.load(f)

        with open(comp_file, encoding="utf-8") as f:
            comp_records = [json.loads(line) for line in f if line.strip()]

        ho_records = [r for r in comp_records if r["dataset"] == "held_out_test_v1.jsonl"]
        computed_ho_acc = sum(1 for r in ho_records if r["routing_correct"]) / len(ho_records)

        reported_ho_acc = metrics["level_a_held_out"]["overall_accuracy"]
        assert abs(computed_ho_acc - reported_ho_acc) < 1e-3, (
            f"Aggregate mismatch: reported {reported_ho_acc}, raw mean {computed_ho_acc}"
        )
