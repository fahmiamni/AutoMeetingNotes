# Audio Transcription Script (Grok STT API)
#
# This script scans the `input/` folder for audio files (.mp3, .m4a, .wav, .ogg, .mp4),
# transcribes each file using the xAI Grok speech-to-text API, and writes a
# corresponding Markdown file into the `output/` folder.
#
# Features: speaker diarization, filler word removal, text normalization.
# No local models required — all processing happens via API.

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
XAI_API_KEY = os.getenv('XAI_API_KEY', '')
XAI_STT_URL = 'https://api.x.ai/v1/stt'
AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.ogg', '.mp4')

# IO paths
input_dir = Path(r'G:\My Drive')
output_dir = Path('output')
output_latest = output_dir / 'latest'
output_transcripts = output_dir / 'transcripts'
output_latest.mkdir(parents=True, exist_ok=True)
output_transcripts.mkdir(parents=True, exist_ok=True)

PROCESSED_TRACKER = output_dir / '.processed_files.json'
BATCH_MANIFEST = output_dir / '.batch_manifest.json'


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_processed_files() -> set:
    if PROCESSED_TRACKER.is_file():
        try:
            return set(json.loads(PROCESSED_TRACKER.read_text(encoding='utf-8')))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_processed_files(processed: set) -> None:
    PROCESSED_TRACKER.write_text(
        json.dumps(sorted(processed), indent=2), encoding='utf-8'
    )


def save_batch_manifest(files: list[dict]) -> None:
    BATCH_MANIFEST.write_text(
        json.dumps(files, indent=2), encoding='utf-8'
    )


def save_transcription_md(text: str, source_path: Path) -> tuple[Path, Path]:
    original_name_output_path = output_transcripts / f'{source_path.stem}.md'
    output_path = output_latest / '02_transcription.md'
    header = '# Transcription completed\n\n'
    content = header + text.strip() + '\n'
    output_path.write_text(content, encoding='utf-8')
    original_name_output_path.write_text(content, encoding='utf-8')
    return output_path, original_name_output_path


# ── Grok STT transcription ────────────────────────────────────────────────────
def transcribe_audio_file(audio_path: Path) -> str:
    """Transcribe an audio file using the xAI Grok STT API."""
    if not XAI_API_KEY:
        raise SystemExit(
            "Error: XAI_API_KEY not set.\n"
            "Set it in .env or as an environment variable."
        )

    headers = {
        'Authorization': f'Bearer {XAI_API_KEY}',
    }

    with open(audio_path, 'rb') as f:
        files = {
            'file': (audio_path.name, f, 'audio/mpeg'),
        }
        data = {
            'diarize': 'true',
            'filler_words': 'false',
            'format': 'true',
            'language': 'en',
        }
        resp = requests.post(XAI_STT_URL, headers=headers, files=files, data=data, timeout=300)

    if resp.status_code != 200:
        raise SystemExit(f"Grok STT error {resp.status_code}: {resp.text}")

    result = resp.json()
    text = result.get('text', '')
    duration = result.get('duration', 0)
    words = result.get('words', [])

    # Build speaker-tagged transcript if diarization data present
    if words and any('speaker' in w for w in words):
        lines = []
        current_speaker = None
        for w in words:
            speaker = w.get('speaker')
            if speaker is not None and speaker != current_speaker:
                current_speaker = speaker
                lines.append(f"\n**Speaker {speaker + 1}:** ")
            lines.append(w['text'] + ' ')
        text = ''.join(lines).strip()

    print(f'  Duration: {duration:.1f}s | Words: {len(words)}')
    return text


# ── Main ──────────────────────────────────────────────────────────────────────
if not XAI_API_KEY:
    print('Error: XAI_API_KEY not set. Add it to .env or set as env var.')
    sys.exit(1)

start_time = time.time()

all_audio_files = sorted([
    f for ext in AUDIO_EXTENSIONS
    for f in input_dir.glob(f'*{ext}')
])

if not all_audio_files:
    print(f'No audio files found in {input_dir}. Supported formats: {", ".join(AUDIO_EXTENSIONS)}')
    print('-' * 50)
    sys.exit(0)

processed_set = load_processed_files()
unprocessed = [f for f in all_audio_files if f.name not in processed_set]

print(f'Total audio files found: {len(all_audio_files)}')
print(f'Already processed: {len(all_audio_files) - len(unprocessed)}')
print(f'New files to process: {len(unprocessed)}')

if not unprocessed:
    print('No new audio files to process.')
    print('-' * 50)
    sys.exit(0)

batch_results = []
for idx, audio_file in enumerate(unprocessed, 1):
    print(f'\n[{idx}/{len(unprocessed)}] Processing: {audio_file.name}')
    try:
        transcription_text = transcribe_audio_file(audio_file)
        saved_path, original_name_saved_path = save_transcription_md(transcription_text, audio_file)
        print(f'  Saved markdown: {saved_path}')
        print(f'  Saved original-name markdown: {original_name_saved_path}')

        processed_set.add(audio_file.name)
        save_processed_files(processed_set)

        batch_results.append({
            'audio_file': audio_file.name,
            'transcript_md': str(original_name_saved_path),
        })
    except SystemExit as e:
        print(f'  Error: {e}')
        continue

save_batch_manifest(batch_results)

end_time = time.time()
elapsed_time = end_time - start_time
print(f'\nBatch complete: {len(batch_results)} file(s) transcribed in {elapsed_time / 60:.2f} minutes')
print('-' * 50)
