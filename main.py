import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -----------------------------------------------------------------------------
# Configuration & Paths
# -----------------------------------------------------------------------------
# 1. Input Directory: Fall back to local 'input' folder if Google Drive is not available
DEFAULT_GDRIVE_DIR = Path(r"G:\My Drive")
if DEFAULT_GDRIVE_DIR.exists():
    INPUT_DIR = DEFAULT_GDRIVE_DIR
else:
    INPUT_DIR = Path("input")
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# 2. Output Directory
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 3. Obsidian Directory (Optional Vault Path)
DEFAULT_OBSIDIAN_DIR = Path(r"C:\Users\ASUS\Documents\famb vault")
OBSIDIAN_DIR = DEFAULT_OBSIDIAN_DIR if DEFAULT_OBSIDIAN_DIR.exists() else None

# 4. Transcription Settings
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")

# 5. API Timeout
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "180"))


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def get_safe_filename(value: str) -> str:
    """Sanitize filename parts to prevent path or OS-related issues."""
    return "".join(char if char.isalnum() or char in ("-", "_", ".") else "_" for char in value)


def is_file_already_processed(stem: str) -> bool:
    """Check if the given audio file stem has already been transcribed and summarized."""
    # Check if local transcription AND summary exist
    local_trans_exists = (OUTPUT_DIR / f"{stem}.md").exists()
    local_summ_exists = (OUTPUT_DIR / f"{stem}_summary.md").exists()
    if local_trans_exists and local_summ_exists:
        return True

    # Check Obsidian directory if configured
    if OBSIDIAN_DIR and OBSIDIAN_DIR.exists():
        for f in OBSIDIAN_DIR.glob("*_summary_*.md"):
            if "_summary_" in f.stem:
                parts = f.stem.split("_summary_")
                # Strip off timestamp (YYYY-MM-DD_HH_MM_SS_ is 20 chars long)
                obsidian_base_name = parts[0][20:]
                if obsidian_base_name == stem:
                    return True
    return False


# -----------------------------------------------------------------------------
# Core Pipeline Steps
# -----------------------------------------------------------------------------
def run_transcription() -> None:
    """Step 1: Transcribe unprocessed MP3 files using local Whisper model."""
    print("=" * 60)
    print("STEP 1: TRANSCRIPTION (Whisper)")
    print("=" * 60)

    # Find all MP3s
    mp3_files = sorted(INPUT_DIR.glob("*.mp3"))
    if not mp3_files:
        print(f"No MP3 files found in: {INPUT_DIR.absolute()}")
        return

    # Filter for unprocessed files
    unprocessed_files = [f for f in mp3_files if not is_file_already_processed(f.stem)]

    if not unprocessed_files:
        print("All audio files are already fully processed (skipping transcription).")
        return

    print(f"Found {len(unprocessed_files)} unprocessed audio file(s).")
    
    # Lazy imports of PyTorch and Whisper to speed up startup of orchestrator
    import torch
    import whisper

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using PyTorch Device: {device.upper()}")
    if device == "cpu":
        print("Warning: GPU (CUDA) is not available. Transcription may be slow.")

    print(f"Loading Whisper Model: '{WHISPER_MODEL}'...")
    model = whisper.load_model(WHISPER_MODEL, device=device)

    for mp3_path in unprocessed_files:
        stem = mp3_path.stem
        print(f"\nTranscribing: {mp3_path.name}")
        start_time = time.time()

        try:
            result = model.transcribe(str(mp3_path))
            transcription_text = result["text"].strip() + "\n"

            # Save file-specific transcript
            out_file = OUTPUT_DIR / f"{stem}.md"
            out_file.write_text(transcription_text, encoding="utf-8")
            print(f"  -> Saved: {out_file.name}")

            # Save generic copy representing the latest run
            latest_file = OUTPUT_DIR / "02_transcription.md"
            latest_file.write_text(transcription_text, encoding="utf-8")

            elapsed = time.time() - start_time
            print(f"  -> Done in {elapsed / 60:.2f} minutes")

        except Exception as e:
            print(f"  -> Error transcribing {mp3_path.name}: {e}")

    print("-" * 60)


def call_llm(prompt: str) -> str:
    """Call the selected AI provider based on environment variables."""
    import requests

    provider = os.getenv("LLM_PROVIDER")
    
    # Auto-detect provider if not explicitly configured
    if not provider:
        if os.getenv("OPENROUTER_API_KEY"):
            provider = "openrouter"
        elif os.getenv("DEEPSEEK_API_KEY"):
            provider = "deepseek"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("GEMINI_API_KEY"):
            provider = "gemini"
        else:
            raise SystemExit(
                "Error: No AI API keys found. Please set one of these in your .env file:\n"
                "  - OPENROUTER_API_KEY\n"
                "  - DEEPSEEK_API_KEY\n"
                "  - OPENAI_API_KEY\n"
                "  - GEMINI_API_KEY"
            )

    provider = provider.lower()
    system_instruction = (
        "You summarize meeting transcripts into clear Markdown notes. "
        "Include concise key points, decisions, and action items when present. "
        "Use plain ASCII Markdown with no emoji."
    )

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        api_url = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        model = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m2.7")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "MeetingNotesSummarizer",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "stream": False,
        }

    elif provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "stream": False,
        }

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        api_url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "stream": False,
        }

    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"temperature": 0.2},
        }

    else:
        raise SystemExit(f"Error: Unsupported LLM provider '{provider}'")

    print(f"    Calling {provider.capitalize()} API (Model: {model})...")
    response = requests.post(api_url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
    
    if response.status_code != 200:
        raise SystemExit(f"API Error ({provider}) status {response.status_code}: {response.text}")
        
    result = response.json()
    
    if provider == "gemini":
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        return result["choices"][0]["message"]["content"].strip()


def run_summarization() -> None:
    """Step 2: Summarize transcripts using selected LLM API."""
    print("=" * 60)
    print("STEP 2: SUMMARIZATION (AI)")
    print("=" * 60)

    # Find transcript files in the output directory
    transcription_files = list(OUTPUT_DIR.glob("*.md"))
    transcription_files = [
        f for f in transcription_files
        if not f.name.endswith("_summary.md") and f.name not in ("02_transcription.md", "05_summarize.md")
    ]

    # Filter out files that already have summaries
    unprocessed_transcripts = [f for f in transcription_files if not is_file_already_processed(f.stem)]

    if not unprocessed_transcripts:
        print("All transcriptions are already summarized.")
        return

    print(f"Found {len(unprocessed_transcripts)} unprocessed transcript(s) to summarize.")

    for trans_path in unprocessed_transcripts:
        stem = trans_path.stem
        print(f"\nSummarizing: {trans_path.name}")
        start_time = time.time()

        try:
            content = trans_path.read_text(encoding="utf-8")
            
            prompt = (
                "Summarize this full meeting transcript into clean Markdown notes.\n\n"
                "Include these sections when information is present:\n"
                "- Key discussion points\n"
                "- Decisions\n"
                "- Action items with owners and deadlines\n"
                "- Important names, fields, prospects, clients, or locations\n\n"
                f"Transcript:\n\n{content}"
            )

            summary = call_llm(prompt)

            # Save file-specific summary
            summary_file = OUTPUT_DIR / f"{stem}_summary.md"
            summary_file.write_text(summary, encoding="utf-8")
            print(f"  -> Saved: {summary_file.name}")

            # Save generic copy representing the latest run
            latest_summary = OUTPUT_DIR / "05_summarize.md"
            latest_summary.write_text(summary, encoding="utf-8")

            # Save to Obsidian Vault if configured
            if OBSIDIAN_DIR and OBSIDIAN_DIR.exists():
                timestamp_prefix = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
                provider = os.getenv("LLM_PROVIDER", "api").lower()
                safe_provider = get_safe_filename(provider)
                
                obsidian_file = OBSIDIAN_DIR / f"{timestamp_prefix}_{stem}_summary_{safe_provider}.md"
                obsidian_file.write_text(summary, encoding="utf-8")
                print(f"  -> Saved to Obsidian: {obsidian_file.name}")

            elapsed = time.time() - start_time
            print(f"  -> Done in {elapsed / 60:.2f} minutes")

        except Exception as e:
            print(f"  -> Error summarizing {trans_path.name}: {e}")

    print("-" * 60)


# -----------------------------------------------------------------------------
# Orchestrator & CLI Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--transcribe":
        run_transcription()
    elif len(sys.argv) > 1 and sys.argv[1] == "--summarize":
        run_summarization()
    else:
        # Main orchestrator mode
        # Spawns transcription and summarization as separate subprocesses to completely
        # release GPU memory after transcription finishes.
        print("=" * 60)
        print("AUTO MEETING NOTES PIPELINE: STARTING")
        print("=" * 60)
        
        # Helper to run script in a subprocess
        def run_step(step_arg: str) -> None:
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            subprocess.run([sys.executable, __file__, step_arg], check=True, env=env)

        start_time = time.time()
        
        # Step 1: Transcription
        run_step("--transcribe")
        
        # Step 2: Summarization
        run_step("--summarize")
        
        total_elapsed = time.time() - start_time
        print("=" * 60)
        print(f"Pipeline completed successfully in {total_elapsed / 60:.2f} minutes!")
        print("=" * 60)
