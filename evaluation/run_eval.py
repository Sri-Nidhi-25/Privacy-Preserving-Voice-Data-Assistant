"""
evaluation/run_eval.py - Unified evaluation CLI.

Usage:
    # Routing evaluation (fast, no audio, calls heuristic _is_data_query)
    python -m evaluation.run_eval --runner routing --seed 42

    # Routing evaluation with LLM tool-call testing (requires Ollama)
    python -m evaluation.run_eval --runner routing --seed 42

    # Transcript correction ablation (requires Ollama)
    python -m evaluation.run_eval --runner correction --seed 42

    # STT transcription quality (requires Whisper + edge-tts)
    python -m evaluation.run_eval --runner transcription --seed 42

    # Obfuscation benchmark (requires Whisper + edge-tts)
    python -m evaluation.run_eval --runner obfuscation --seed 42

    # Full end-to-end (requires Whisper + Ollama + edge-tts)
    python -m evaluation.run_eval --runner e2e --seed 42

    # Run all text-only evaluations (no audio required)
    python -m evaluation.run_eval --runner all-text --seed 42
"""
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Privacy-Preserving Voice Assistant Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--runner",
        choices=["routing", "correction", "transcription", "obfuscation", "e2e", "all-text"],
        required=True,
        help="Which evaluation runner to execute",
    )
    parser.add_argument(
        "--dataset",
        default="evaluation/datasets/voice_eval_v1.jsonl",
        help="Path to the evaluation dataset (JSONL)",
    )
    parser.add_argument(
        "--output",
        default="evaluation/results",
        help="Directory to write evaluation results",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Limit number of cases (useful for quick smoke tests)",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM calls (routing runner only) - evaluate heuristic only",
    )
    args = parser.parse_args()

    dataset = Path(args.dataset)
    output = Path(args.output)
    seed = args.seed

    if not dataset.exists():
        print(f"ERROR: Dataset not found: {dataset}")
        sys.exit(1)

    output.mkdir(parents=True, exist_ok=True)

    if args.runner == "routing" or args.runner == "all-text":
        from evaluation.runners.routing_runner import run as routing_run
        routing_run(dataset, output, seed=seed, skip_llm=args.skip_llm)

    if args.runner == "correction" or args.runner == "all-text":
        from evaluation.runners.correction_runner import run as correction_run
        correction_run(dataset, output, seed=seed)

    if args.runner == "transcription":
        from evaluation.runners.transcription_runner import run as transcription_run
        transcription_run(dataset, output, seed=seed, max_cases=args.max_cases)

    if args.runner == "obfuscation":
        from evaluation.runners.obfuscation_runner import run as obfuscation_run
        obfuscation_run(dataset, output, seed=seed, max_cases=args.max_cases)

    if args.runner == "e2e":
        from evaluation.runners.end_to_end_runner import run as e2e_run
        e2e_run(dataset, output, seed=seed, max_cases=args.max_cases)


if __name__ == "__main__":
    main()
