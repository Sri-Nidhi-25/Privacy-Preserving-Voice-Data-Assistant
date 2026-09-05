# Privacy-Preserving Voice Data Assistant

A complete, end‑to‑end voice query system that:
- **Obfuscates** the speaker’s voice (pitch shifts while preserving formants) to protect identity.
- **Transcribes** the query with OpenAI Whisper.
- **Routes** the intent via an LLM (Ollama) to the correct internal data source (CRM, support tickets, or analytics).
- **Responds** with a natural‑language answer and optional audio (TTS).

This is a self‑contained FastAPI service with mock data connectors, designed for demonstration and extension.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration (.env)](#configuration-env)
- [API Endpoints](#api-endpoints)
- [Testing the Voice Query](#testing-the-voice-query)
- [Using Docker](#using-docker)
- [Known Issues & Workarounds](#known-issues--workarounds)
- [Future Improvements / Roadmap](#future-improvements--roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature | How It Works |
|---------|--------------|
| **Speaker obfuscation** | Uses the WORLD vocoder to shift pitch (F0) while keeping the spectral envelope (formants) intact. This preserves transcription accuracy far better than naive pitch‑shifting. |
| **Speech‑to‑Text** | Whisper (configurable model, default `base`) with a multi‑temperature decoding strategy to mitigate hallucinations. Confidence scores are computed and used to reject low‑quality audio. |
| **Intent classification & tool calling** | An LLM (Ollama) decides whether to query CRM, support tickets, or analytics. It can call functions with validated arguments. |
| **Text‑to‑Speech** | Edge TTS (free, no API key) converts the answer to an MP3 file. |
| **Transcript correction** | An LLM‑based pre‑processing step corrects garbled domain‑specific words (e.g., “tickets” → “tick it”) before routing, reducing misclassification. |
| **REST API** | Clean endpoints for health checks, raw data access (debugging), and voice queries. |
| **Docker support** | Containerised deployment with Ollama included. |

---

## Architecture Overview

```
┌─────────────┐      ┌────────────────────┐      ┌─────────────────┐
│  User       │      │  FastAPI Router    │      │  Obfuscator     │
│ (upload MP3)│─────▶│  (/voice/query)    │─────▶│  (WORLD vocoder)│
└─────────────┘      └────────────────────┘      └─────────────────┘
                            │                            │
                            ▼                            │
                     ┌────────────────────┐              │
                     │  STT (Whisper)     │◀─────────────┘
                     │  + confidence      │
                     └────────────────────┘
                            │
                            ▼
                     ┌────────────────────┐
                     │  LLM Orchestrator  │
                     │  - correction      │
                     │  - tool call       │
                     └────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │   CRM    │ │ Support  │ │Analytics │
         │Connector │ │Connector │ │Connector │
         └──────────┘ └──────────┘ └──────────┘
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                     ┌────────────────────┐
                     │  TTS (Edge TTS)    │
                     │  (answer audio)    │
                     └────────────────────┘
                            │
                            ▼
                     ┌────────────────────┐
                     │  JSON Response     │
                     │  + audio URLs      │
                     └────────────────────┘
```

- **Obfuscator** – implemented in `app/voice/obfuscator.py` as `FormantPreservingObfuscator`. Uses `pyworld`, `librosa`, and `soundfile`.
- **STT** – `app/voice/stt.py`. Loads audio with `librosa` (bypasses FFmpeg) and passes a NumPy array to Whisper.
- **LLM Orchestrator** – `app/services/llm_orchestrator.py`. Handles correction prompt, tool definitions, validation, and execution.
- **Connectors** – mock data sources in `app/connectors/`. They return lists of dicts from JSON files.
- **TTS** – `app/voice/tts.py`. Uses Edge TTS.

---

## Project Structure (after restructuring)

```
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── crm_connector.py
│   │   ├── support_connector.py
│   │   └── analytics_connector.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   └── voice.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── data.py
│   │   └── voice.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_orchestrator.py
│   │   ├── business_rules.py
│   │   ├── data_identifier.py
│   │   └── voice_optimizer.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   └── security.py
│   └── voice/
│       ├── __init__.py
│       ├── obfuscator.py
│       ├── stt.py
│       └── tts.py
├── data/                     (create this; place your mock JSON files here)
│   ├── customers.json
│   ├── support_tickets.json
│   └── analytics.json
├── temp_audio/               (auto‑created; used for temporary audio files)
├── .env.example
├── .env                      (copy from example)
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── benchmark_obfuscation.py  (optional benchmarking script)
└── README.md
```

---

## Prerequisites

- **Python 3.10+**
- **Ollama** – installed locally, or use the Docker setup.
- **(Optional) FFmpeg** – recommended for broader audio format support, though the STT engine loads audio via `librosa` and can handle many formats without it. However, for MP3/WebM decoding on some systems, `librosa` may fall back to FFmpeg – installing it is a safe bet.

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Sri-Nidhi-25/Privacy-Preserving-Voice-Data-Assistant.git
cd Privacy-Preserving-Voice-Data-Assistant
```

### 2. Create a Virtual Environment (recommended)
```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
```bash
cp .env.example .env
```
Edit `.env` to adjust:
- `OBFUSCATION_STRENGTH` – `mild`, `medium`, or `strong`.
- `STT_MODEL` – Whisper model size (e.g., `base`, `small.en`, `medium.en`).
- `OLLAMA_MODEL` – ensure no trailing space (e.g., `llama3.2:latest`).
- `EDGE_TTS_VOICE` – any Edge TTS voice name.
- `API_KEY` – your secret key for the voice endpoint.

### 5. Prepare Mock Data
Create the `data/` directory and populate it with three JSON files. Example structures:

**`customers.json`**:
```json
[{"id": 1, "name": "Alice", "status": "active"}, ...]
```

**`support_tickets.json`**:
```json
[{"ticket_id": 101, "status": "open", "priority": "high"}, ...]
```

**`analytics.json`**:
```json
[{"metric": "daily_active_users", "value": 1234, "date": "2026-01-01"}, ...]
```

If any file is missing, the connectors now return an empty list gracefully (error handling added).

### 6. Run the Server
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

---

## Configuration (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `"Voice Data Assistant"` |
| `MAX_RESULTS` | Maximum number of records to return in a query | `10` |
| `OBFUSCATION_STRENGTH` | `mild`, `medium`, or `strong` | `mild` |
| `STT_MODEL` | Whisper model name | `base` |
| `OLLAMA_MODEL` | Ollama model to use | `llama3.2:latest` |
| `EDGE_TTS_VOICE` | Edge TTS voice | `en-US-GuyNeural` |
| `API_KEY` | Authentication for `/voice/query` | `secret-key-change-me` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Returns `{"status": "ok"}`. |
| `GET` | `/data/{source}` | Returns raw mock data from `crm`, `support`, or `analytics` (debugging only). |
| `POST` | `/voice/query` | Main voice query endpoint. Requires `api-key` header and `audio_file` multipart data. |

### POST `/voice/query`

**Request:**
- Header: `api-key: <your_key>`
- Body: `multipart/form-data` with key `audio_file` containing the audio file.

**Supported audio formats:** WAV, MP3, WebM, OGG. Internally, they are loaded via `librosa` (no FFmpeg required for basic formats, but FFmpeg may be needed for exotic ones).

**Response (JSON):**
```json
{
  "obfuscated_audio_url": "/static/<obfuscated_file>.wav",
  "answer_audio_url": "/static/<answer_file>.mp3",
  "transcript": "Show me all high priority open tickets",
  "answer_text": "Found 3 open high-priority tickets.",
  "metadata": {
    "data_sources_used": ["support"],
    "result_count": 3,
    "freshness": "Data as of 2026-09-05T12:00:00Z",
    "tool_calls": [...],
    "low_confidence_transcription": false,
    "stt_confidence": { "avg_logprob": -0.45, "no_speech_prob": 0.12, ... }
  }
}
```

- If the STT confidence is low, the system returns a generic “Sorry, I didn’t catch that” without calling the LLM.
- The audio URLs point to files served from `temp_audio/`; they are automatically cleaned up after the response is sent (via `BackgroundTasks`).

---

## Testing the Voice Query

## Test
```bash
curl http://localhost:8000/health
curl http://localhost:8000/data/crm
```

Using `curl` (Windows users: use `curl.exe`):

```bash
curl -X POST http://localhost:8000/voice/query \
  -H "api-key: secret-key-change-me" \
  -F "audio_file=@path/to/your_audio.mp3;type=audio/mpeg" 
```

Replace `path/to/your_audio.mp3` with a real file. Supported types: `audio/wav`, `audio/mpeg`, `audio/webm`, `audio/ogg`.

---

## Using Docker

### 1. Build and start containers
```bash
docker-compose up --build
```

### 2. Pull the Ollama model (inside the container)
```bash
docker exec -it <ollama_container_name> ollama pull llama3.2:latest
```
(Replace `<ollama_container_name>` with the actual container name, e.g., `ollama`.)

### 3. Access the API
The service will be available at `http://localhost:8000`.

```bash
curl.exe -X POST http://127.0.0.1:8000/voice/query -H "api-key: secret-key-change-me" -F "audio_file=@newtest.mp3;type=audio/mpeg"
```
Testing the data

```bash
python -c "import json; data=json.load(open('data/support_tickets.json')); r=[t for t in data if t['priority']=='high' and t['status']=='open']; print(len(r)); [print(t) for t in r]" 

python -c "import json; data=[d for d in json.load(open('data/analytics.json')) if d['metric']=='daily_active_users'][:7]; print(sum(d['value'] for d in data)/len(data))"

```
---

## Known Issues & Workarounds

| Issue | Workaround / Status |
|-------|---------------------|
| **Audio pre‑conversion not implemented** | The system expects the uploaded file to be readable by `librosa`. For most browser‑uploaded MP3/WebM files, this works. For corrupted `.mpeg` files with embedded JSON, it may fail. **Workaround:** Use clean WAV/MP3 files. A fix (converting to 16kHz mono WAV before obfuscation) is planned. |
| **FFmpeg optional but recommended** | While `librosa` handles many formats, installing FFmpeg improves robustness. |
| **Temp files cleanup** | **Fixed** – files are deleted after response via `BackgroundTasks`. |
| **Mock JSON files missing** | **Fixed** – connectors now return `[]` gracefully. |
| **Large result set summarisation** | **Fixed** – summarisation now occurs before limiting; the LLM returns a summary count. |
| **Jitter too high for `mild`** | **Fixed** – jitter is now `0.5` for mild, `1.5` for others. |
| **`/data` endpoint ignores `limit`** | This endpoint is for debugging only; the voice pipeline uses `MAX_RESULTS` properly. Not fixed, but not critical. |
| **Ollama model name trailing space** | **Fixed** in `.env` and `config.py`. |

---

## Future Improvements / Roadmap

1. **Audio pre‑conversion** – automatically resample and downmix to 16kHz mono WAV before obfuscation, to guarantee compatibility with `soundfile`.
2. **Real data connectors** – replace mock JSON with actual database/API integrations (e.g., PostgreSQL, REST APIs).
3. **Streaming responses** – return TTS audio as a stream instead of saving to disk.
4. **Enhanced confidence rejection** – allow user to retry with clearer speech.
5. **Multi‑language support** – expand Whisper to other languages and adjust correction prompts accordingly.
6. **Benchmark automation** – integrate the benchmark script into CI/CD to track WER regression.
7. **Frontend UI** – a simple web interface for testing (the existing `voice_chat.html` can be updated).
8. **Security hardening** – use JWT or OAuth2 instead of a simple API key, and implement rate limiting.
9. **Logging & monitoring** – structured logs, metrics, and alerts.
10. **Docker optimisation** – reduce image size and improve startup time.

---
## License

This project is open‑source under the [MIT License](https://choosealicense.com/licenses/mit/).

---