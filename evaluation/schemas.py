"""
evaluation/schemas.py - Shared data schemas for all evaluation records.

Every evaluation case produces an EvalRecord. Runners populate it.
Reporters read it.  The format is stable so results from different runs
can be compared.
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
import json


DATASET_VERSION = "v1"
EVAL_VERSION = "2"  # increment when evaluation logic changes


@dataclass
class EvalRecord:
    """
    Structured result for a single evaluated case.
    All fields are required in the final record.
    Optional fields are None until the corresponding stage runs.
    """
    # --- Provenance ---
    run_id: str
    case_id: str
    dataset_id: str
    dataset_version: str
    timestamp: str
    git_commit: str
    python_version: str
    eval_version: str = EVAL_VERSION

    # --- Model config ---
    stt_model: str = ""
    llm_model: str = ""
    obfuscation_method: str = "none"
    obfuscation_strength: str = "none"
    random_seed: int = 42

    # --- Input ---
    input_text: str = ""          # ground-truth text (what was said)
    category: str = ""
    subcategory: str = ""

    # --- Ground truth ---
    expected_route: str = ""       # "tool" | "direct"
    expected_tool: Optional[str] = None
    expected_args: Dict[str, Any] = field(default_factory=dict)

    # --- STT stage ---
    stt_transcript: Optional[str] = None
    stt_wer: Optional[float] = None
    stt_cer: Optional[float] = None
    stt_avg_logprob: Optional[float] = None
    stt_no_speech_prob: Optional[float] = None
    stt_compression_ratio: Optional[float] = None
    stt_low_confidence_decision: Optional[bool] = None

    # --- Correction stage ---
    correction_attempted: Optional[bool] = None
    correction_accepted: Optional[bool] = None
    correction_rejected: Optional[bool] = None
    correction_changed: Optional[bool] = None
    corrected_transcript: Optional[str] = None
    corrected_wer: Optional[float] = None
    corrected_cer: Optional[float] = None
    correction_improvement: Optional[float] = None   # WER_raw - WER_corrected (positive = improvement)
    correction_degraded: Optional[bool] = None        # corrected_wer > stt_wer

    # --- Routing stage ---
    actual_route: Optional[str] = None     # "tool" | "direct"
    routing_correct: Optional[bool] = None

    # --- Tool selection stage ---
    actual_tool: Optional[str] = None
    tool_selection_correct: Optional[bool] = None

    # --- Tool arguments stage ---
    actual_args: Optional[Dict[str, Any]] = None
    args_exact_match: Optional[bool] = None
    args_semantic_match: Optional[bool] = None    # after coercion/normalization
    args_field_accuracy: Optional[float] = None   # fraction of expected fields correct

    # --- Connector / answer ---
    connector_success: Optional[bool] = None
    answer_text: Optional[str] = None
    result_count: Optional[int] = None

    # --- End-to-end ---
    end_to_end_success: Optional[bool] = None
    failure_stage: Optional[str] = None    # from taxonomy
    failure_reason: Optional[str] = None

    # --- Latency (ms) ---
    latency_ms: Dict[str, int] = field(default_factory=dict)

    # --- Privacy / obfuscation metrics ---
    obfuscation_pitch_shift_semitones: Optional[float] = None
    privacy_metric: Optional[str] = "not_yet_measured"   # placeholder per spec

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvalRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
