# AutoMeetingNotes

Automate your meeting notes — from audio recording to a clean, summarized Markdown document in minutes.

The entire pipeline is consolidated into **a single, simplified, and extremely robust file: `main.py`**.

## How It Works

The pipeline executes in two isolated stages to ensure GPU memory is completely released between steps:

```
MP3 Audio File  →  [Whisper Transcription]  →  [AI Summarization]  →  Markdown Notes
```

1. **Transcription (Stage 1)** — Converts unprocessed MP3 recordings into raw Markdown text using OpenAI's Whisper model (local GPU/CPU, no API costs).
2. **Summarization (Stage 2)** — Automatically summarizes the transcripts into clean, structured Markdown notes with key discussion points, decisions, and action items using your choice of local or cloud AI models.

---

## Project Structure

```
AutoMeetingNotes/
├── main.py                         # The central script (runs the entire pipeline)
├── requirements.txt                # Project dependencies
├── .env                            # API Keys & Configurations
├── input/                          # Fallback folder for your input MP3 files
├── output/                         # Local transcripts and summaries are saved here
├── Archieve/                       # Old and alternative script variations
└── working/                        # Local research and development scripts
```

---

## Features

- **Consolidated Codebase**: Only one script to run (`main.py`) which manages both orchestration and individual steps.
- **Auto-Avoid Redundancy**: Automatically checks local files and your Obsidian vault so it never wastes time or API tokens on already-processed files.
- **Smart Directory Detection**: Scans `G:\My Drive` by default; falls back to the local `input/` folder automatically if Google Drive is not connected.
- **Dynamic Multi-Provider AI Support**: Seamlessly supports summarizing via **OpenRouter**, **DeepSeek**, **OpenAI**, or **Gemini** out-of-the-box using lightweight requests (no heavy SDKs required).
- **Obsidian Integration**: If your Obsidian Vault is detected, copies are instantly saved there with clean, searchable dates and model stamps.

---

## Setup & Usage

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/fahmiamni/AutoMeetingNotes.git
cd AutoMeetingNotes
pip install -r requirements.txt
```

### 2. Configure your `.env`

Add your keys and preferred models to the `.env` file:

```env
# Choose your provider: openrouter | deepseek | openai | gemini
LLM_PROVIDER=openrouter

# Add your API Key(s)
OPENROUTER_API_KEY=your_openrouter_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Optional Customizations
WHISPER_MODEL=large-v3-turbo
```

### 3. Run the Pipeline

Simply run the unified `main.py` script:

```bash
python main.py
```

- To run **only transcription**: `python main.py --transcribe`
- To run **only summarization**: `python main.py --summarize`

---

## Notes & Technical Details

- **Automatic GPU memory release**: To release graphics memory, running `python main.py` triggers stage 1 and stage 2 in separate isolated subprocesses of itself.
- **Supported Providers**:
  - **OpenRouter**: Default model is `minimax/minimax-m2.7`.
  - **DeepSeek**: Default model is `deepseek-chat`.
  - **OpenAI**: Default model is `gpt-4o-mini`.
  - **Gemini**: Default model is `gemini-2.5-flash`.
