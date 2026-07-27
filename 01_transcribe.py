# Audio Transcription Script
# 
# This script scans the `input/` folder for audio files (.mp3, .m4a, .wav, .ogg, .mp4),
# transcribes each file locally using Whisper `large-v3-turbo`, and writes a corresponding
# Markdown file into the `output/` folder.
#
# Supports dual Whisper backends (set via WHISPER_BACKEND env var):
#   - openai-whisper (default): Original OpenAI Whisper
#   - faster-whisper: CTranslate2-based, ~4x faster transcription
#
# Before running: install required packages and make sure your Python environment can load 
# the Whisper model. If you encounter memory issues, switch to a smaller Whisper model name 
# such as `small` or `tiny`.

import os
import sys
import json
import subprocess
from pathlib import Path
import numpy as np
import torch
import time
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# Backend selection (env var overrides default)
WHISPER_BACKEND = os.getenv('WHISPER_BACKEND', 'openai-whisper')
if WHISPER_BACKEND not in ('openai-whisper', 'faster-whisper'):
    print(f'[WARN] Unknown WHISPER_BACKEND="{WHISPER_BACKEND}". Falling back to openai-whisper.')
    WHISPER_BACKEND = 'openai-whisper'

print(f'Whisper backend: {WHISPER_BACKEND}')


def install(package):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


SAMPLE_RATE = 16000
AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.ogg', '.mp4')

def load_audio(audio_path: str) -> np.ndarray:
    """Load an audio file and return a 16 kHz mono numpy array.
    Uses whisper.load_audio (robust ffmpeg-backed loader) when openai-whisper is
    installed; falls back to faster-whisper's internal av-based loader otherwise."""
    try:
        import whisper
        return whisper.load_audio(audio_path)
    except ImportError:
        pass
    try:
        from faster_whisper.audio import decode_audio
        return decode_audio(audio_path, sampling_rate=SAMPLE_RATE)
    except ImportError:
        raise RuntimeError(
            'No audio loader available. Install openai-whisper or faster-whisper.'
        )


# IO paths
input_dir = Path(r'G:\My Drive')
output_dir = Path('output')
output_latest = output_dir / 'latest'
output_transcripts = output_dir / 'transcripts'
output_latest.mkdir(parents=True, exist_ok=True)
output_transcripts.mkdir(parents=True, exist_ok=True)

# Device / compute type
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Using device: {device}')
if device == 'cpu':
    print('Torch CUDA is not available. Install a CUDA-enabled PyTorch build to use GPU.')

model_name = os.getenv('WHISPER_MODEL', 'large-v3-turbo')

# Chunking settings
CHUNK_SECONDS = int(os.getenv('WHISPER_CHUNK_SECONDS', '30'))
OVERLAP_SECONDS = int(os.getenv('WHISPER_OVERLAP_SECONDS', '5'))
STEP_SECONDS = CHUNK_SECONDS - OVERLAP_SECONDS


def split_audio_into_chunks(audio_path: str):
    """Load audio and split into overlapping fixed-length chunks.
    Returns list of (start_time_in_seconds, audio_chunk_array)."""
    audio = load_audio(audio_path)
    total_samples = len(audio)
    chunk_samples = CHUNK_SECONDS * SAMPLE_RATE
    step_samples = STEP_SECONDS * SAMPLE_RATE

    chunks = []
    start = 0
    while start < total_samples:
        end = min(start + chunk_samples, total_samples)
        chunk = audio[start:end]
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)))
        chunks.append((start / SAMPLE_RATE, chunk))
        start += step_samples

    return chunks


def merge_chunk_texts(chunks):
    """Merge transcribed chunks, trimming overlap from each chunk after the first.
    chunks: list of (start_time, text) sorted by start_time."""
    if not chunks:
        return ""
    chunks.sort(key=lambda x: x[0])
    overlap_ratio = OVERLAP_SECONDS / CHUNK_SECONDS
    full_text = chunks[0][1]
    for i in range(1, len(chunks)):
        curr_text = chunks[i][1]
        words = curr_text.split()
        skip_count = int(len(words) * overlap_ratio)
        skip_count = min(skip_count, len(words) - 3)
        if skip_count > 0:
            curr_text = ' '.join(words[skip_count:])
        full_text += '\n' + curr_text
    return full_text.strip()


# ── Backend-specific model loading ──────────────────────────────────────────
if WHISPER_BACKEND == 'faster-whisper':
    from faster_whisper import WhisperModel

    compute_type = os.getenv('WHISPER_COMPUTE_TYPE',
                             'float16' if device == 'cuda' else 'int8')
    print(f'Loading faster-whisper model: {model_name} on {device} ({compute_type})')
    model = WhisperModel(model_name, device=device, compute_type=compute_type,
                         cpu_threads=int(os.getenv('WHISPER_CPU_THREADS', '4')),
                         num_workers=1)

    beam_size = int(os.getenv('WHISPER_BEAM_SIZE', '5'))

    def transcribe_chunk(chunk_audio: np.ndarray) -> str:
        segments, _ = model.transcribe(chunk_audio, beam_size=beam_size)
        return ' '.join(seg.text.strip() for seg in segments)
else:
    import whisper

    print(f'Loading openai-whisper model: {model_name} on {device}')
    model = whisper.load_model(model_name, device=device)

    def transcribe_chunk(chunk_audio: np.ndarray) -> str:
        result = model.transcribe(chunk_audio)
        return result['text'].strip()


# ── Unified transcription pipeline ──────────────────────────────────────────
def transcribe_audio_file(audio_path: Path) -> str:
    """Transcribe a single audio file locally using Whisper with chunked processing."""
    audio_chunks = split_audio_into_chunks(str(audio_path))

    if len(audio_chunks) == 1:
        return transcribe_chunk(audio_chunks[0][1])

    print(f'  Audio split into {len(audio_chunks)} chunks ({CHUNK_SECONDS}s ea, {OVERLAP_SECONDS}s overlap)')
    results = []
    with tqdm(audio_chunks, desc='  Transcribing', unit='chunk') as pbar:
        for start_time, chunk_audio in pbar:
            end_time = start_time + CHUNK_SECONDS
            pbar.set_postfix_str(f'{start_time:.0f}s - {end_time:.0f}s')
            text = transcribe_chunk(chunk_audio)
            results.append((start_time, text))

    return merge_chunk_texts(results)


def save_transcription_md(text: str, source_path: Path) -> tuple[Path, Path]:
    original_name_output_path = output_transcripts / f'{source_path.stem}.md'
    output_path = output_latest / '02_transcription.md'
    header = '# Transcription completed\n\n'
    content = header + text.strip() + '\n'
    output_path.write_text(content, encoding='utf-8')
    original_name_output_path.write_text(content, encoding='utf-8')
    return output_path, original_name_output_path


# ── Processed files tracking ─────────────────────────────────────────────────
PROCESSED_TRACKER = output_dir / '.processed_files.json'
BATCH_MANIFEST = output_dir / '.batch_manifest.json'


def load_processed_files() -> set:
    if PROCESSED_TRACKER.is_file():
        try:
            data = json.loads(PROCESSED_TRACKER.read_text(encoding='utf-8'))
            return set(data)
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


# ── Main execution ──────────────────────────────────────────────────────────
start_time = time.time()

all_audio_files = sorted([
    f for ext in AUDIO_EXTENSIONS
    for f in input_dir.glob(f'*{ext}')
])

if not all_audio_files:
    print(f'No audio files found in {input_dir}. Supported formats: {", ".join(AUDIO_EXTENSIONS)}')
    print("-" * 50)
    sys.exit(0)

processed_set = load_processed_files()
unprocessed = [f for f in all_audio_files if f.name not in processed_set]

print(f'Total audio files found: {len(all_audio_files)}')
print(f'Already processed: {len(all_audio_files) - len(unprocessed)}')
print(f'New files to process: {len(unprocessed)}')

if not unprocessed:
    print('No new audio files to process.')
    print("-" * 50)
    sys.exit(0)

batch_results = []
for idx, audio_file in enumerate(unprocessed, 1):
    print(f'\n[{idx}/{len(unprocessed)}] Processing: {audio_file.name}')
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

save_batch_manifest(batch_results)

end_time = time.time()
elapsed_time = end_time - start_time
print(f'\nBatch complete: {len(batch_results)} file(s) transcribed in {elapsed_time / 60:.2f} minutes')
print("-" * 50)
