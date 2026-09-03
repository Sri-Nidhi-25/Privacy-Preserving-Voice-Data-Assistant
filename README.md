# Privacy-Preserving Voice Data Assistant

FastAPI service that takes a voice query, strips the speaker's voice fingerprint
(pitch/time obfuscation), transcribes it (Whisper), routes it to the right data
source via an LLM tool-calling step (Ollama), and reads the answer back (ElevenLabs TTS).

## Endpoints
- `GET /health` — liveness check
- `GET /data/{source}` — `source` in `crm`, `support`, `analytics`; raw REST access to mock data
- `POST /voice/query` — multipart `audio_file` (wav/mp3) + `api-key` header → JSON with transcript, answer text, and audio URLs

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```
## Prerequisites

Install FFmpeg:

```powershell
winget install Gyan.FFmpeg
```

Verify:

```powershell
ffmpeg -version
```

Example conversion:

```powershell
ffmpeg -i test.m4a -codec:a libmp3lame -q:a 2 test.mp3
```
```
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe

$newPath = "$userPath;C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"

[Environment]::SetEnvironmentVariable("Path", $newPath, "User")
```

## Run with Docker
```bash
docker-compose up --build
docker exec -it <ollama_container> ollama pull llama3.1:8b
```

## Test
```bash
curl http://localhost:8000/health
curl http://localhost:8000/data/crm
curl.exe -X POST http://127.0.0.1:8000/voice/query -H "api-key: secret-key-change-me" -F "audio_file=@mictestwithsnaps.mp3;type=audio/mpeg"
```
```bash
curl.exe -X POST http://127.0.0.1:8000/voice/query -H "api-key: secret-key-change-me" -F "audio_file=@newtest.mp3;type=audio/mpeg"

python -c "import json; data=json.load(open('data/support_tickets.json')); r=[t for t in data if t['priority']=='high' and t['status']=='open']; print(len(r)); [print(t) for t in r]" 

python -c "import json; data=[d for d in json.load(open('data/analytics.json')) if d['metric']=='daily_active_users'][:7]; print(sum(d['value'] for d in data)/len(data))"

```
