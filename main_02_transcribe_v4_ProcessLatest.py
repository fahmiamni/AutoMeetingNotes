# Audio Transcription Script
# 
# This script scans the `input/` folder for MP3 files, transcribes each file locally 
# using Whisper `large-v3-turbo`, and writes a corresponding Markdown file into the `output/` folder.
#
# Before running: install required packages and make sure your Python environment can load 
# the Whisper model. If you encounter memory issues, switch to a smaller Whisper model name 
# such as `small` or `tiny`.

# Install required Python packages if not already installed
import os
import sys
import subprocess

def install(package):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

'''
# Install required packages if not already installed
packages = ['openai-whisper']
for pkg in packages:
    try:
        __import__(pkg.replace('-', '_'))
    except ImportError:
        install(pkg)
'''

from pathlib import Path
import numpy as np
import torch
import whisper
import time

input_dir = Path(r'G:\My Drive')
output_dir = Path('output')
output_dir.mkdir(parents=True, exist_ok=True)

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Using device: {device}')
if device == 'cpu':
    print('Torch CUDA is not available. Install a CUDA-enabled PyTorch build to use GPU.')

model_name = 'large-v3-turbo'

print(f'Loading Whisper model: {model_name} on {device}')
model = whisper.load_model(model_name, device=device)


# Chunking settings (adjust via env vars if needed)
SAMPLE_RATE = 16000
CHUNK_SECONDS = int(os.getenv('WHISPER_CHUNK_SECONDS', '30'))
OVERLAP_SECONDS = int(os.getenv('WHISPER_OVERLAP_SECONDS', '5'))
STEP_SECONDS = CHUNK_SECONDS - OVERLAP_SECONDS


def split_audio_into_chunks(audio_path: str):
    """Load audio and split into overlapping fixed-length chunks.
    Returns list of (start_time_in_seconds, audio_chunk_array)."""
    audio = whisper.load_audio(audio_path)
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


def transcribe_mp3_file(mp3_path: Path) -> str:
    """Transcribe a single MP3 file locally using Whisper with chunked processing."""
    audio_chunks = split_audio_into_chunks(str(mp3_path))

    if len(audio_chunks) == 1:
        result = model.transcribe(audio_chunks[0][1])
        return result['text']

    print(f'  Audio split into {len(audio_chunks)} chunks ({CHUNK_SECONDS}s ea, {OVERLAP_SECONDS}s overlap)')
    results = []
    for i, (start_time, chunk_audio) in enumerate(audio_chunks):
        end_time = start_time + CHUNK_SECONDS
        print(f'  Transcribing chunk {i+1}/{len(audio_chunks)} ({start_time:.0f}s - {end_time:.0f}s)...')
        result = model.transcribe(chunk_audio)
        text = result['text'].strip()
        results.append((start_time, text))

    return merge_chunk_texts(results)

def save_transcription_md(text: str, source_path: Path) -> tuple[Path, Path]:
    original_name_output_path = output_dir / f'{source_path.stem}.md'
    output_path = output_dir / '02_transcription.md'
    header = '# Transcription completed\n\n'
    content = header + text.strip() + '\n'
    output_path.write_text(content, encoding='utf-8')
    original_name_output_path.write_text(content, encoding='utf-8')
    return output_path, original_name_output_path


# Main execution
start_time = time.time()
mp3_files = sorted(input_dir.glob('*.mp3'))

if not mp3_files:
    print(f'No MP3 files found in {input_dir}. Add a single MP3 file there and rerun.')
elif len(mp3_files) > 1:
    print(f'More than one MP3 file was found in {input_dir}.')
    print('Found files:')
    for mp3_file in mp3_files:
        print(f'  - {mp3_file.name}')
    mp3_file = mp3_files[-1] #Process the last file in the list
    print(f'Processing: {mp3_file.name}')
    transcription_text = transcribe_mp3_file(mp3_file)
    saved_path, original_name_saved_path = save_transcription_md(transcription_text, mp3_file)
    print(f'  Saved markdown: {saved_path}')
    print(f'  Saved original-name markdown: {original_name_saved_path}')

else:
    mp3_file = mp3_files[0]
    print(f'Processing: {mp3_file.name}')
    transcription_text = transcribe_mp3_file(mp3_file)
    saved_path, original_name_saved_path = save_transcription_md(transcription_text, mp3_file)
    print(f'  Saved markdown: {saved_path}')
    print(f'  Saved original-name markdown: {original_name_saved_path}')

end_time = time.time()
elapsed_time = end_time - start_time
print(f'Time taken to run the code (transcription): {elapsed_time / 60:.2f} minutes')
print("-" * 50)
