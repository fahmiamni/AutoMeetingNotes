# AutoMeetingNotes

Automate your meeting notes — from audio recording to a clean, summarized Markdown document in minutes.

## How It Works

The pipeline has two stages, orchestrated by `main.py` (locally) or `docker-compose.yml` (Docker):

```
Audio File  →  [01_transcribe.py]  →  [02_summarize_or.py]  →  Markdown Notes
                     Whisper              OpenRouter API           OneNote
```

1. **Transcription** (`01_transcribe.py`) — Transcribes audio files locally using Whisper `large-v3-turbo` (via `faster-whisper`, no API needed). Long recordings are processed in 30-second chunks with 5-second overlap.
2. **Summarization** (`02_summarize_or.py`) — Sends each transcript to OpenRouter and generates clean structured notes, then saves them to your OneNote notebook (`save_notes.py`).

## Project Structure

```
AutoMeetingNotes/
├── output/                         # Generated files appear here
│   ├── transcripts/                # Named transcript files
│   ├── summaries/                  # Named summary files
│   ├── latest/                     # Latest run (overwritten each time)
│   │   ├── 02_transcription.md     # Raw transcript
│   │   └── 05_summarize.md         # AI-generated summary
│   ├── .processed_files.json       # Audio files already transcribed
│   ├── .batch_manifest.json        # Transcripts pending summarization
│   └── .summarized_tracking.json   # Summaries already generated
├── Dockerfile                      # Container image (python:3.12-slim + ffmpeg)
├── docker-compose.yml              # Long-running input-folder worker
├── .env.example                    # Configuration template
├── main.bat                        # Windows launcher (venv Python)
├── main.py                         # Orchestrator — runs the full pipeline
├── 01_transcribe.py                # Stage 1: transcription
├── 02_summarize_or.py              # Stage 2: summarization via OpenRouter
├── save_notes.py                   # Saves notes to OneNote
├── summarizer_template.md          # Prompt template for the summarizer
└── requirements.txt
```

## Setup

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/fahmiamni/AutoMeetingNotes.git
cd AutoMeetingNotes
pip install -r requirements.txt
```

Requires **Python 3.12** and a CUDA-enabled GPU (recommended). The default PyTorch build targets CUDA 12.1 — see `--extra-index-url` in `requirements.txt`.

### 2. Configure `.env`

```bash
cp .env.example .env
```

```ini
# Input folder (host path mounted into the container)
INPUT_DIR=G:\My Drive

# Transcription
WHISPER_BACKEND=faster-whisper
WHISPER_MODEL=large-v3-turbo

# Summarization
OPENROUTER_API_KEY=your_key_here
# OPENROUTER_MODEL=google/gemini-3-flash-preview

# OneNote saving
MATON_API_KEY=your_key_here
ONENOTE_NOTEBOOK_NAME=...
ONENOTE_SECTION_NAME=...
```

Full list of optional environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `INPUT_DIR` | `input` | Folder scanned for audio files |
| `WHISPER_BACKEND` | `openai-whisper` | `faster-whisper` (recommended) or `openai-whisper` |
| `WHISPER_MODEL` | `large-v3-turbo` | Whisper model name |
| `WHISPER_CHUNK_SECONDS` | `30` | Audio chunk length |
| `WHISPER_OVERLAP_SECONDS` | `5` | Overlap between chunks |
| `WHISPER_COMPUTE_TYPE` | `float16` (GPU) / `int8` (CPU) | faster-whisper compute type |
| `WHISPER_CPU_THREADS` | `4` | CPU threads for faster-whisper |
| `WHISPER_BEAM_SIZE` | `5` | Decode beam size |
| `OPENROUTER_API_URL` | `https://openrouter.ai/api/v1/chat/completions` | Summarization endpoint |
| `OPENROUTER_MODEL` | `google/gemini-3-flash-preview` | Summarization model |
| `SUMMARY_MAX_TOKENS` | `30000` | Max tokens per summary |
| `OPENROUTER_TIMEOUT_SECONDS` | `180` | API request timeout |

## Usage

### Local (Windows)

1. Drop your meeting audio (`.mp3`, `.m4a`, `.wav`, `.ogg`, `.mp4`) into the folder set by `INPUT_DIR` (default: `./input`)
2. Run `main.bat` (or `python main.py`). Add `--watch` to keep the local process
   waiting for new audio files.

### Docker

1. Set `INPUT_DIR` in `.env` to the **absolute host path** containing your audio files
2. Start the worker:

```bash
docker compose build
docker compose up -d
```

The `worker` stays running and checks the mounted `/app/input` folder every 5 seconds. It waits until a new audio file has stopped changing for 10 seconds, then transcribes and summarizes it. Already-processed files are skipped. These timings can be adjusted with `WATCH_POLL_SECONDS` and `WATCH_STABLE_SECONDS`.

View worker logs with `docker compose logs -f worker`. Stop it with `docker compose down`. Transcripts, summaries, and tracking state live in the shared `pipeline-output` volume, and the Whisper model cache persists in the `hf-cache` volume across restarts.

To copy generated files from the volume:

```bash
docker compose cp worker:/app/output ./output-docker
```

### ⚠️ The `input` folder is locked (Linux)

If `input/` does not exist when you first run `docker compose up`, the Docker daemon creates it as **root**, and your user can't write to it (a lock icon in your file manager). Two ways to avoid this:

- **Recommended:** create the folder yourself before the first run — `mkdir -p input`. A clone of this repo already includes `input/.gitkeep`, so the folder exists and is owned by you; no action needed.
- **Fix an already-locked folder:** `sudo chown $USER:$USER input`

Don't delete and recreate `input/` with `sudo` — that recreates it as root-owned.

The pipeline will automatically:
- Transcribe each new audio file → `output/latest/02_transcription.md` + `output/transcripts/{name}.md`
- Summarize each transcript → `output/latest/05_summarize.md` + `output/summaries/{name}_summary.md`
- Save each summary to your OneNote notebook

Already-processed audio files are skipped on subsequent runs.

## Notes

- The summarizer prompt comes from `summarizer_template.md` (system message + `---` + user prompt with a `{transcript}` placeholder); the script falls back to built-in defaults if missing or malformed
- Summarization input is capped at ~50,000 characters by default (configurable via `MAX_INPUT_CHARS`)
- Notes are saved to OneNote via the Maton API (`MATON_API_KEY`, notebook/section names in `.env`)
