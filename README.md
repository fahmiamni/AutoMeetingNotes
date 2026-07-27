# AutoMeetingNotes

Automate your meeting notes — from audio recording to a clean, summarized Markdown document in minutes.

## How It Works

The pipeline has two stages:

```
MP3 Audio File  →  [Whisper Transcription]  →  [AI Summarization]  →  Markdown Notes
```

1. **Transcription** — Converts an MP3 recording into raw text using OpenAI's Whisper model (local, no API needed)
2. **Summarization** — Turns the transcript into clean, structured notes with key points and action items using a local or API-based AI model

## Project Structure

```
AutoMeetingNotes/
├── input/                          # Place your MP3 file here
│   └── (your meeting recording.mp3)
├── output/                         # Generated files appear here
│   ├── transcripts/                # Named transcript files
│   ├── summaries/                  # Named summary files
│   └── latest/                     # Latest run (overwritten each time)
│       ├── 02_transcription.md     # Raw transcript
│       └── 05_summarize.md         # AI-generated summary
├── Archieve/                       # Older/scratch scripts
├── main.py                         # Run this — executes full pipeline
├── main_02_transcribe_v1.py       # Transcription (local input folder)
├── main_02_transcribe_v2_Gdrive.py # Transcription (reads from Google Drive)
├── main_02_transcribe_v3_LargeV3.py # Transcription (Whisper large-v3 model)
├── main_05_summarize_v1_API_Gpt4o_mini.py  # Summarization via OpenAI GPT-4o mini
├── main_05_summarize_v2_local_Gemma4_E2b.py # Summarization via local Gemma 4 E2B
└── requirements.txt
```

## Setup

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/fahmiamni/AutoMeetingNotes.git
cd AutoMeetingNotes
pip install -r requirements.txt
```

### 2. Install Whisper

Whisper is required for transcription:

```bash
pip install openai-whisper
```

### 3. Set Up AI Summarization (choose one)

**Option A — OpenAI API (GPT-4o mini)**
```bash
# Add to your environment or .env file
export OPENAI_API_KEY=your_key_here
```
Then edit `main.py` to use `main_05_summarize_v1_API_Gpt4o_mini.py`.

**Option B — Local (Gemma 4 E2B via Hugging Face)**
```bash
export HF_MODEL_ID=google/gemma-4-E2B-it
export HF_LOCAL_FILES_ONLY=0   # Run once to download the model
python main_05_summarize_v2_local_Gemma4_E2b.py
```

GPU strongly recommended for local summarization. Set `HF_DEVICE=cuda` if CUDA is available.

## Usage

### Standard Flow (local input folder)

1. Drop your meeting MP3 into the `input/` folder
2. Run:

```bash
python main.py
```

The script will automatically:
- Find the MP3 file in `input/`
- Transcribe it → saves `output/latest/02_transcription.md` + `output/transcripts/{name}.md`
- Summarize it → saves `output/latest/05_summarize.md` + `output/summaries/{name}_summary.md`

### Google Drive Input (v2)

If you want to read directly from Google Drive, edit `main_02_transcribe_v2_Gdrive.py` and set:

```python
input_dir = Path(r'G:\My Drive')  # Your GDrive path
```

### Choose Transcription Version

| Script | Model | Input Source |
|--------|-------|-------------|
| `main_02_transcribe_v1.py` | Whisper large-v3-turbo | `input/` folder |
| `main_02_transcribe_v2_Gdrive.py` | Whisper large-v3-turbo | Google Drive |
| `main_02_transcribe_v3_LargeV3.py` | Whisper large-v3 | Custom path |

To switch, edit `main.py` and change the script path before running.

### Choose Summarization Method

Edit `main.py` and uncomment the summarizer you want to use:

```python
run_script("main_05_summarize_v1_API_Gpt4o_mini.py")    # OpenAI API
run_script("main_05_summarize_v2_local_Gemma4_E2b.py")  # Local Gemma 4
```

## Requirements

- Python 3.10+
- PyTorch (CUDA recommended)
- `openai-whisper`
- `transformers` + `accelerate` (for local Gemma)
- `openai` (for API summarization)
- `python-dotenv`

Full list in `requirements.txt`.

## Notes

- Only one MP3 file should be in the `input/` folder at a time
- Summarization input is capped at ~50,000 characters by default (configurable via `MAX_INPUT_CHARS`)
- Transcript is saved to `output/latest/02_transcription.md` and `output/transcripts/{name}.md`; summary to `output/latest/05_summarize.md` and `output/summaries/{name}_summary.md`