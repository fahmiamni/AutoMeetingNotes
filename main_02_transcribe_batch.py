import sys
import subprocess
from pathlib import Path
import torch
import whisper
import time


def install(package):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


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


def transcribe_mp3_file(mp3_path: Path) -> str:
    result = model.transcribe(str(mp3_path))
    return result['text']


def save_transcription_md(text: str, source_path: Path) -> Path:
    output_path = output_dir / f'{source_path.stem}.md'
    content = text.strip() + '\n'
    output_path.write_text(content, encoding='utf-8')
    return output_path


def transcribe_single_file(mp3_path: Path) -> Path:
    print(f'  Transcribing: {mp3_path.name}')
    transcription_text = transcribe_mp3_file(mp3_path)
    saved_path = save_transcription_md(transcription_text, mp3_path)
    print(f'  Saved: {saved_path.name}')
    return saved_path


def get_all_unprocessed_mp3s(obsidian_dir: Path) -> list[Path]:
    mp3_files = sorted(input_dir.glob('*.mp3'))
    
    if not mp3_files:
        print(f'No MP3 files found in {input_dir}')
        return []
    
    processed_stems = set()
    if obsidian_dir.exists():
        for f in obsidian_dir.glob('*_summary_*.md'):
            stem = f.stem
            parts = stem.split('_')
            if len(parts) >= 3:
                processed_stems.add('_'.join(parts[1:-1]))
    
    unprocessed = []
    for mp3 in mp3_files:
        if mp3.stem not in processed_stems:
            unprocessed.append(mp3)
        else:
            print(f'  Skipping (already processed): {mp3.name}')
    
    return unprocessed


if __name__ == '__main__':
    obsidian_dir = Path(r'C:\Users\ASUS\Documents\famb vault')
    
    start_time = time.time()
    
    unprocessed_files = get_all_unprocessed_mp3s(obsidian_dir)
    
    if not unprocessed_files:
        print('No unprocessed MP3 files found.')
    else:
        print(f'Found {len(unprocessed_files)} unprocessed MP3 file(s)')
        
        for mp3_file in unprocessed_files:
            try:
                transcribe_single_file(mp3_file)
            except Exception as e:
                print(f'  Error transcribing {mp3_file.name}: {e}')
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Total transcription time: {elapsed_time / 60:.2f} minutes')
    print("-" * 60)
   