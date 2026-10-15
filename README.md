# Privacy-Preserving Voice Data Assistant

A local, privacy-preserving voice query assistant that combines speaker voice obfuscation, automatic speech recognition (Whisper), domain transcript correction, selective abstention, tool-calling, and text-to-speech synthesis — all running locally with no data leaving the machine.

---

## Architecture: Full Pipeline

```text
Audio Upload (WAV, MP3, WebM, OGG, MPEG)
  │
  ▼
1. Audio Validation
     Size limit, duration checks, decodability check (pydub/ffmpeg)
     → Rejects corrupt, silent, or oversized files before any processing
  │
  ▼
2. Voice Obfuscation  (FormantPreservingObfuscator — WORLD Vocoder)
     Pitch-shifts the speaker's F0 (fundamental frequency) by a configurable
     semitone amount while preserving spectral envelope, so Whisper STT still
     works accurately on the obfuscated audio.
     Intensities: mild (±2 st) | medium (±4 st) | strong (±6 st) | very_strong (±8 st)
     Gaussian jitter is added to the shift so consecutive requests are not identical.
  │
  ▼
3. Speech-to-Text  (OpenAI Whisper — local, offline)
     Transcribes the obfuscated audio. Returns confidence signals:
     avg_logprob, no_speech_prob, compression_ratio.
     Low-confidence results (avg_logprob < -1.0) trigger early abstention.
  │
  ▼
4. Correction Guard  (LLM pass via Ollama)
     Fixes domain-specific transcription errors:
     "high priority" vs "hai priority", "inactive" vs "in active", etc.
     Includes overlap and refusal guardrails — refuses corrections that
     change intent or introduce hallucinations.
  │
  ▼
5. Intent Routing
     Classifies the corrected transcript into one of:
       crm_query | support_query | analytics_query | multi_domain | unknown
     Uses keyword matching + LLM classification with a fallback chain.
  │
  ▼
6. Selective Abstention  (Evidence-Grounded Abstention Engine)
     Decouples Domain Entity Evidence (E_domain) from Operational Speech-Act
     Evidence (E_op) and Distractor Penalty (D_dist):
       EXECUTE : High domain + high operational evidence, low distractor penalty
       ABSTAIN : Domain vocabulary present but missing operational evidence,
                 or high distractor penalty (narrative, conversational, cross-domain)
       DIRECT  : No domain vocabulary — routed straight to LLM for a plain answer
     Prevents false-positive tool execution on semantic distractors
     (e.g. "What is today's weather like?" must NOT trigger CRM tools).
     Can be toggled on/off per-request from the UI or via query param.
  │
  ▼
7. Tool Execution  (LLM Orchestrator → Connectors)
     The LLM selects and calls the appropriate tool:
       get_crm_data       → data/customers.json
       get_support_tickets → data/support_tickets.json
       get_analytics_data  → data/analytics.json
     Tool arguments are validated and coerced before any connector is called.
     Invalid arguments are rejected — connectors are NEVER called with bad args.
     Multi-domain queries (e.g. "inactive customers with open tickets") perform
     an inner join by customer_id across CRM + Support results.
     Results are capped at 10 records for voice readability; the UI shows
     "10/N records" when the total exceeds the cap.
  │
  ▼
8. TTS Synthesis  (Edge-TTS — en-US-AriaNeural)
     Synthesises the answer text into speech.
     TTS failure is handled gracefully — the text answer is always preserved
     in the response even if audio generation fails.
  │
  ▼
API JSON Response
  • answer_text          — plain text answer
  • answer_audio_url     — URL to synthesised MP3
  • obfuscated_audio_url — URL to obfuscated WAV (for inspection)
  • transcript           — corrected STT transcript
  • metadata             — request_id, sources, result count, abstention decision,
                          obfuscation strength/shift, STT confidence, per-stage latency
```

---

## Project Structure

```text
.
├── app/
│   ├── config.py                  # Settings, obfuscation strength aliases, startup validation
│   ├── failure.py                 # Central FailureType enum + PipelineError
│   ├── main.py                    # FastAPI app, CORS, error handlers, static file mount
│   ├── voice_chat.html            # Served copy of the UI (kept in sync with root)
│   ├── connectors/
│   │   ├── base.py                # BaseConnector, freshness evaluation
│   │   ├── crm_connector.py       # Reads data/customers.json, filters by status/tier/name
│   │   ├── support_connector.py   # Reads data/support_tickets.json, filters by priority/status
│   │   └── analytics_connector.py # Reads data/analytics.json, DAU trends, averages
│   ├── models/
│   │   ├── common.py              # DataResponse, Metadata Pydantic schemas
│   │   └── voice.py               # VoiceQueryResponse schema
│   ├── routers/
│   │   ├── health.py              # GET /health/live, GET /health/ready
│   │   ├── data.py                # GET /data/{source} — direct data debug endpoint
│   │   └── voice.py               # POST /voice/query — main pipeline endpoint
│   ├── services/
│   │   ├── abstention_router.py   # Evidence-grounded abstention engine (EXECUTE/ABSTAIN/DIRECT)
│   │   ├── business_rules.py      # Voice result limits (MAX_RESULTS cap)
│   │   ├── correction_guard.py    # LLM-based domain transcript correction with guardrails
│   │   ├── data_identifier.py     # Infers data type from record structure
│   │   ├── intent_router.py       # Classifies transcript into domain intent
│   │   ├── llm_orchestrator.py    # Tool selection, argument coercion/validation, connector calls
│   │   └── voice_optimizer.py     # summarize_if_large() — compresses large result sets
│   ├── utils/
│   │   ├── logging.py             # Structured JSON logging, ISO-8601 timestamps
│   │   └── security.py            # API key validation middleware
│   └── voice/
│       ├── audio_validation.py    # File size, duration, decodability checks
│       ├── obfuscator.py          # FormantPreservingObfuscator (WORLD vocoder) + VoiceObfuscator
│       ├── stt.py                 # STTEngine — Whisper with confidence signals
│       └── tts.py                 # Edge-TTS synthesis with graceful fallback
├── data/
│   ├── customers.json             # Mock CRM records
│   ├── support_tickets.json       # Mock support tickets
│   └── analytics.json             # Mock daily active user analytics
├── tests/
│   ├── conftest.py                # Shared fixtures (WAV file, TestClient)
│   ├── test_api.py                # POST /voice/query endpoint tests
│   ├── test_audio_validation.py   # Audio validation edge cases
│   ├── test_config.py             # Settings, obfuscation strength alias resolution
│   ├── test_connectors.py         # CRM / Support / Analytics connector tests
│   ├── test_correction.py         # Correction guard LLM pass tests
│   ├── test_health.py             # Health probe endpoint tests
│   ├── test_invariants.py         # Safety invariants (bad args never reach connectors)
│   ├── test_obfuscation.py        # Obfuscator output verification
│   ├── test_routing.py            # Intent classification tests
│   ├── test_stt.py                # Whisper STT confidence signal tests
│   ├── test_tool_validation.py    # Tool arg coercion + validation (limit, priority, status)
│   └── test_phase5_5/
│       ├── test_pipeline_integration.py  # Real obfuscator + STT + LLM integration tests
│       └── test_abstention_e2e.py        # Abstention router end-to-end with mocks
├── evaluation/
│   └── benchmark_obfuscation.py   # Benchmark: WER + routing fidelity across obfuscation strengths
├── benchmark_audio/               # Generated outputs from benchmark runs (phrase WAVs, results.csv)
├── temp_audio/                    # Ephemeral per-request audio files (auto-cleaned)
├── voice_chat.html                # Browser UI (served at http://127.0.0.1:8000/)
├── .env                           # Local config (not committed)
├── .env.example                   # Config template
├── requirements.txt               # All dependencies
├── Dockerfile                     # Container build
└── docker-compose.yml             # App + Ollama sidecar
```

---

## Setup & Running Locally

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) running locally with `llama3.2:latest` pulled
- `ffmpeg` on PATH (used by pydub/librosa for audio decoding)

### 1. Create and activate virtual environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure environment
```powershell
Copy-Item .env.example .env
```

Edit `.env` with your desired settings:
```env
API_KEY=secret-key-change-me
OBFUSCATION_STRENGTH=mild        # mild | medium | strong | high | very_strong
STT_MODEL=small.en
OLLAMA_MODEL=llama3.2:latest
LLM_TIMEOUT_SECONDS=120.0
```

### 4. Start the server
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000/** in your browser to use the voice assistant UI.

> The `--reload` flag watches for file changes and restarts automatically during development.

---

## Configuration Reference (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | *(required)* | Server API key. UI uses `dev-insecure-key` which maps to the default. |
| `OBFUSCATION_STRENGTH` | `mild` | Global default obfuscation strength. Can be overridden per-request from the UI dropdown. |
| `STT_MODEL` | `small.en` | Whisper model name (`tiny`, `base`, `small`, `medium`, `large`). |
| `OLLAMA_MODEL` | `llama3.2:latest` | Ollama model for correction guard + tool selection. |
| `LLM_TIMEOUT_SECONDS` | `120.0` | Timeout for Ollama LLM calls. |
| `MAX_RESULTS` | `10` | Maximum records returned to the voice pipeline per query. |
| `ALLOWED_ORIGINS` | `http://127.0.0.1:8000` | CORS allowed origins (comma-separated). |

---

## Obfuscation Intensities

| Strength | Semitone Shift | Jitter | Alias(es) |
|----------|---------------|--------|-----------|
| `mild` | ±2 st | 0.5 | — |
| `medium` | ±4 st | 1.0 | — |
| `strong` | ±6 st | 1.0 | `high` |
| `very_strong` | ±8 st | 1.5 | `verystrong`, `very strong` |

The shift sign (raise/lower pitch) is randomised per request. Gaussian jitter means no two requests produce identical shifts. Obfuscation intensity can be changed:
- **Per-request** via the UI dropdown (persisted in localStorage)
- **Globally** via `OBFUSCATION_STRENGTH` in `.env` (hot-reloaded per request, no restart needed)

---

## API Reference

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health/live` | Fast liveness check → `{"status": "alive"}` |
| `GET` | `/health/ready` | Deep readiness check (Whisper, Ollama, TTS, data files) → `ready / degraded / unavailable` |
| `GET` | `/health` | Alias for `/health/ready` |

### Data (Debug)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/data/{source}?limit=10` | Returns raw records from `crm`, `support`, or `analytics` |

### Voice Query
```
POST /voice/query
  ?obfuscation_strength=mild     # optional — overrides .env default for this request
  ?enable_abstention=true        # optional — default true

Headers:
  api-key: dev-insecure-key

Body (multipart/form-data):
  audio_file: <WAV | MP3 | WebM | OGG | MPEG>
```

**Example with curl:**
```powershell
curl.exe -X POST "http://127.0.0.1:8000/voice/query?enable_abstention=true" `
  -H "api-key: dev-insecure-key" `
  -F "audio_file=@your_query.mpeg;type=audio/mpeg"
```

**Response JSON:**
```json
{
  "answer_text": "Found 3 open high-priority support tickets.",
  "answer_audio_url": "/static/abc123.answer.mp3",
  "obfuscated_audio_url": "/static/abc123.obf.wav",
  "transcript": "How many open high priority tickets are there?",
  "metadata": {
    "request_id": "c7f7663e-72ba-4b53-9d41-3b74ad50c4ce",
    "data_sources_used": ["support"],
    "result_count": 3,
    "abstention_decision": "EXECUTE",
    "abstention_confidence": 1,
    "abstention_reason": "High domain + operational evidence detected.",
    "execution_prevented_by_abstention": false,
    "obfuscation_strength": "mild",
    "obfuscation_details": {
      "strength": "mild",
      "base_semitones": 2.0,
      "actual_shift_semitones": 2.09
    },
    "stt_confidence": {
      "avg_logprob": -0.35,
      "no_speech_prob": 0.01,
      "compression_ratio": 1.1,
      "low_confidence": false
    },
    "latency_ms": {
      "validation": 25,
      "obfuscation": 2100,
      "stt": 5800,
      "correction": 4200,
      "routing": 2,
      "tts": 1500,
      "total": 13627
    }
  }
}
```

---

## Running Tests

```powershell
.\venv\Scripts\python.exe -m pytest tests/ -v
```

Test coverage:

| Test File | What it covers |
|-----------|---------------|
| `test_config.py` | Settings parsing, all obfuscation strength aliases |
| `test_audio_validation.py` | Size limits, duration checks, corrupt file rejection |
| `test_obfuscation.py` | Formant-preserving obfuscator output across all 4 intensities |
| `test_stt.py` | Whisper confidence signal extraction, low-confidence detection |
| `test_correction.py` | Correction guard LLM pass, refusal guardrails |
| `test_routing.py` | Intent classification, `_is_data_query` edge cases |
| `test_tool_validation.py` | Argument coercion (limit, priority, status), invalid arg rejection |
| `test_connectors.py` | CRM / Support / Analytics connector filter logic |
| `test_invariants.py` | Safety invariants — invalid tool args never reach connectors |
| `test_health.py` | Health probe liveness and readiness endpoints |
| `test_api.py` | POST /voice/query end-to-end with mocked STT/LLM/TTS |
| `test_phase5_5/` | Pipeline integration + abstention router end-to-end |

---

## Obfuscation Benchmark

Measures Word Error Rate (WER) and tool routing fidelity across obfuscation strengths on a fixed set of 8 test phrases:

```powershell
.\venv\Scripts\python.exe evaluation/benchmark_obfuscation.py --seed 42
```

Outputs to `benchmark_audio/`:
- `phrase_N.mp3` — raw TTS-synthesised audio
- `phrase_N_{strength}.wav` — obfuscated versions for each intensity
- `results.csv` — WER + routing pass/fail per phrase × strength combination

---

## Key Design Decisions

**Why WORLD vocoder instead of simple resampling?**
Simple pitch resampling changes speech duration and distorts formants, making Whisper transcription unreliable. The WORLD vocoder separates F0 (pitch) from spectral envelope, so only pitch is shifted while formants remain intact — preserving STT accuracy while still meaningfully obfuscating speaker identity.

**Why Evidence-Grounded Abstention instead of a simple confidence threshold?**
A confidence threshold on the LLM alone causes false positives on distractor queries that mention domain vocabulary casually (e.g. "I used to work in customer support"). The abstention engine separately scores domain evidence (E_domain), operational retrieval intent (E_op), and distractor penalty (D_dist) before deciding whether to execute a tool call.

**Why validate tool arguments before calling connectors?**
The LLM occasionally generates structurally incorrect arguments (e.g. `{"limit": "all"}` for a counting query). Coercing and validating before the connector is called ensures the safety invariant: invalid tool arguments can never reach the data layer.

**Why hot-reload `.env` per request instead of at startup?**
Allows changing `OBFUSCATION_STRENGTH` (or any other setting) in `.env` and having it take effect immediately on the next request without restarting the server — useful during development.
