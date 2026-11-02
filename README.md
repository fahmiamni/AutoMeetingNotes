# AutoMeetingNotes

Automate your meeting notes — from audio recording to a clean, summarized Markdown document in minutes.

## How It Works

The pipeline has two stages, orchestrated by `main.py`:

```
Audio File  →  [01_transcribe.py]  →  [02_summarize_or.py]  →  Markdown Notes
                     Whisper              OpenRouter API           Obsidian / OneNote
```

1. **Transcription** (`01_transcribe.py`) — Transcribes audio files locally using Whisper `large-v3-turbo` (via `faster-whisper`, no API needed). Long recordings are processed in 30-second chunks with 5-second overlap.
2. **Summarization** (`02_summarize_or.py`) — Sends each transcript to OpenRouter and generates clean structured notes, then saves them to your Obsidian vault and OneNote notebook (`save_notes.py`).

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
├── main.bat                        # Windows launcher (venv Python)
├── main.py                         # Orchestrator — runs the full pipeline
├── 01_transcribe.py                # Stage 1: transcription
├── 02_summarize_or.py              # Stage 2: summarization via OpenRouter
├── save_notes.py                   # Saves notes to Obsidian + OneNote
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

```ini
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

1. Drop your meeting audio (`.mp3`, `.m4a`, `.wav`, `.ogg`, `.mp4`) into **`G:\My Drive`** (Google Drive desktop folder — this path is configured in `01_transcribe.py`)
2. Run `main.bat` (or `python main.py`)

The pipeline will automatically:
- Transcribe each new audio file → `output/latest/02_transcription.md` + `output/transcripts/{name}.md`
- Summarize each transcript → `output/latest/05_summarize.md` + `output/summaries/{name}_summary.md`
- Save each summary to your Obsidian vault and OneNote notebook

Already-processed audio files are skipped on subsequent runs.

## Notes

- The summarizer prompt comes from `summarizer_template.md` (system message + `---` + user prompt with a `{transcript}` placeholder); the script falls back to built-in defaults if missing or malformed
- Summarization input is capped at ~50,000 characters by default (configurable via `MAX_INPUT_CHARS`)
- Summaries are saved to Obsidian at `C:\Users\ASUS\Documents\famb vault` (hardcoded in `save_notes.py`)
