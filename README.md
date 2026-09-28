# Privacy-Preserving Voice Data Assistant (Phase 1 Prototype)

A local, privacy-preserving voice query assistant that performs speaker voice obfuscation, automatic speech recognition (Whisper), domain transcript correction, query classification, data retrieval, and text-to-speech synthesis (Edge-TTS).

> **Deployment Note:** This is an evaluation-ready local prototype designed for controlled experimentation and reliability measurement. It is intended for local single-node development, not high-concurrency enterprise cloud deployment.

---

## 1. Core Architecture Pipeline

```text
Audio Upload (WAV, MP3, WebM, OGG)
  │
  ▼
1. Audio Validation Layer (size, decodability, duration checks)
  │
  ▼
2. Formant-Preserving Obfuscation (WORLD Vocoder F0 pitch shifting)
  │
  ▼
3. Speech-to-Text (Whisper STT with multi-temperature retry + confidence scores)
  │  ├── [Low confidence detected] ──▶ Abstain (safely prompt user for retry)
  ▼  └── [Acceptable confidence]
4. Domain Transcript Correction (LLM pass with overlap & refusal guardrails)
  │
  ▼
5. Routing & Tool Argument Validation (Schema-checked parameters)
  │  ├── [Invalid tool arguments] ──▶ Reject immediately; connector NEVER executed
  ▼  └── [Valid tool arguments]
6. Connector Execution (Mock CRM, Support, Analytics connectors)
  │
  ▼
7. Answer Generation & Voice Optimization (Summarization + voice limiting)
  │
  ▼
8. Text-to-Speech Synthesis (Edge-TTS with fallback preservation of text)
  │
  ▼
API JSON Response + Static Audio URLs + Observable Stage Latency & Metadata
```

---

## 2. Phase 1 Reliability & Observability Improvements

- **Central Failure Taxonomy:** Centralized `FailureType` enum and `PipelineError` in `app/failure.py` preventing raw stack traces or internal filesystem paths from leaking to clients.
- **Audio Validation:** Explicit pre-processing validation (`app/voice/audio_validation.py`) checking file existence, size, duration limits, and audio decodability before running vocoders or Whisper.
- **Temporary File Lifecycle:** Guaranteed cleanup of raw user audio uploads and intermediate uncompressed WAV files in `try ... finally` blocks on both success and failure paths. Periodic background cleaner prunes stale files.
- **Structured JSON Logging:** Machine-readable event logging with ISO-8601 UTC timestamps, unique `request_id`, stage labels, and latency durations. Raw user speech and transcripts are withheld from logs by default.
- **Request Traceability:** Unique UUID4 `request_id` generated for every incoming request and propagated through logs and response metadata.
- **Stage-Level Latency:** Timing measurements in milliseconds for `validation`, `obfuscation`, `stt`, `orchestrator`, `tts`, and `total` request duration.
- **Honest Data Freshness:** Clear distinction between `retrieved_at` (query execution time) and `source_last_updated` (actual underlying data modification time). Unknown timestamps are reported honestly as `"unknown"`.
- **Liveness & Readiness Health Probes:**
  - `GET /health/live`: Fast process liveness check.
  - `GET /health/ready`: Deep dependency readiness check inspecting Whisper, Ollama, TTS, and data file availability, returning `ready`, `degraded`, or `unavailable`.
- **Configurable CORS & Startup Validation:** Fail-fast validation in `app/config.py` validating models, timeouts, limits, and origins at startup.

---

## 3. Project Structure

```text
.
├── app/
│   ├── config.py                 # Hardened configuration & startup validation
│   ├── failure.py                # Central FailureType taxonomy & PipelineError
│   ├── main.py                   # FastAPI app, CORS, error handlers, static mount
│   ├── connectors/               # Data connectors (BaseConnector, CRM, Support, Analytics)
│   ├── models/                   # Pydantic schemas (common, voice)
│   ├── routers/                  # API routers (voice, data, health)
│   ├── services/                 # LLM orchestration, business rules, summarization
│   ├── utils/                    # Structured JSON logging, API key security
│   └── voice/                    # Audio validation, WORLD obfuscator, Whisper STT, TTS
├── data/                         # Mock JSON data files (customers, tickets, analytics)
├── docs/
│   └── reliability_invariants.md # Core safety & behavioral invariants
├── evaluation/                   # Reproducible experiment benchmarks
│   ├── benchmark_obfuscation.py
│   └── README.md
├── tests/                        # Comprehensive automated test suite
├── temp_audio/                   # Ephemeral directory for audio processing
├── voice_chat.html               # Single-page browser audio recording client
├── .env.example                  # Environment configuration template
└── requirements.txt              # Application and testing dependencies
```

---

## 4. Setup & Running Locally

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) running locally with `llama3.2:latest`

### 1. Installation
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Ensure your `.env` contains your desired `API_KEY` and settings.

### 3. Run FastAPI Service
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/` in your browser to interact with the voice client.

---

## 5. API Reference

### Health Probes
- `GET /health/live`: Returns `{"status": "alive"}`.
- `GET /health/ready`: Returns component readiness details (`whisper`, `ollama`, `tts`, `crm`, `support`, `analytics`).
- `GET /health`: Backward-compatible alias for `/health/ready`.

### Data Endpoints (Debugging)
- `GET /data/{source}?limit=10`: Returns mock data records from `crm`, `support`, or `analytics`.

### Voice Query
- `POST /voice/query`
  - **Headers:** `api-key: <API_KEY>`
  - **Body (multipart/form-data):** `audio_file` (WAV, MP3, WebM, OGG)
  - **Response (JSON):**
    ```json
    {
      "obfuscated_audio_url": "/static/xxx.obf.wav",
      "answer_audio_url": "/static/xxx.answer.mp3",
      "transcript": "Show me all high priority open tickets",
      "answer_text": "Found 3 support tickets.",
      "metadata": {
        "request_id": "c7f7663e-72ba-4b53-9d41-3b74ad50c4ce",
        "data_sources_used": ["support"],
        "result_count": 3,
        "retrieved_at": "2026-09-14T14:30:00.000Z",
        "source_last_updated": "2026-09-14T12:00:00.000Z",
        "low_confidence_transcription": false,
        "stt_confidence": {
          "avg_logprob": -0.21,
          "no_speech_prob": 0.01,
          "compression_ratio": 1.05,
          "low_confidence": false
        },
        "latency_ms": {
          "validation": 25,
          "obfuscation": 180,
          "stt": 820,
          "orchestrator": 450,
          "tts": 320,
          "total": 1795
        }
      }
    }
    ```

---

## 6. Running Automated Tests

Run the complete 201-test suite covering config, audio validation, obfuscation, STT, correction, routing, tool validation, connectors, health states, fault injection, calibration, metamorphic relations, and evaluation pipeline self-validation:

```bash
pytest tests/ -v
```

---

## 7. Phase 4 — Research-Grade Evaluation & Experiment Reproduction

Phase 4 establishes research-grade evaluation, out-of-distribution robustness, and empirical privacy-utility analysis without synthetic or fabricated metrics:

### A. Master Experiment Suite (Single Command)
Run all Phase 4 experiments (held-out generalization, challenge stress, systematic ablation, acoustic privacy profiling, and audio perturbation matrix) with a single reproducible command:

```bash
python -m evaluation.run_final_experiment --output-dir experiments/results --seed 42
```

Outputs are automatically serialized to:
- `experiments/results/master_experiment_manifest_latest.json` (provenance, git commit, seed, metric matrices)
- `experiments/results/dashboard.html` (interactive, self-contained visual results dashboard)

### B. Individual Evaluation Modules
- **Held-Out Generalization Set:** `evaluation/datasets/held_out_test/held_out_test_v1.jsonl` (30 unseen cases evaluating syntactic and lexical generalization)
- **Adversarial Challenge Set:** `evaluation/datasets/challenge/challenge_v1.jsonl` (25 cases covering STT-misleading queries, subtle sentiment, contradictory filters, and boundary conditions)
- **Metamorphic Invariant Testing:** `tests/test_phase4/test_metamorphic.py` (16 invariant tests across paraphrase groups and correction traps)
- **Evaluation Pipeline Integrity:** `tests/test_phase4/test_evaluation_pipeline_integrity.py` (12 self-validation tests defending against division-by-zero, corrupted schemas, and metric boundary errors)
- **Systematic Ablation Study:** `python -m evaluation.runners.ablation_runner` (quantifies the empirical impact of disabling the intent router, correction guard, tool-alignment check, and bounded retries)
- **Empirical Acoustic Privacy Profile:** `python -m evaluation.runners.privacy_acoustic_runner` (extracts objective physical fundamental frequency shifts $\Delta F_0$ via YIN algorithm rather than arbitrary 'privacy scores')
- **Environmental Audio Robustness Matrix:** `python -m evaluation.runners.robustness_runner` (evaluates acoustic feature drift under additive Gaussian noise 10dB–$\infty$, playback tempo 0.85x–1.15x, and volume scaling -6dB–+6dB)

### C. Research Documentation
- [Phase 4 Initial Audit & RQs](docs/phase4_initial_audit.md)
- [Privacy Threat Model](docs/privacy_threat_model.md)
- [Claim Audit & Empirical Verification](docs/claim_audit.md)
- [Final Research Evaluation Report](docs/final_evaluation_report.md)
- [Reliability Invariants (16 Invariants)](docs/reliability_invariants.md)

