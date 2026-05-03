# Audio Transcription Script
# 
# This script scans the `input/` folder for MP3 files, transcribes each file locally 
# using Whisper `large-v3-turbo`, and writes a corresponding Markdown file into the `output/` folder.
#
# Before running: install required packages and make sure your Python environment can load 
# the Whisper model. If you encounter memory issues, switch to a smaller Whisper model name 
# such as `small` or `tiny`.

# Install required Python packages if not already installed
import sys
import subprocess

def install(package):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

packages = ['openai-whisper']
for pkg in packages:
    try:
        __import__(pkg.replace('-', '_'))
    except ImportError:
        install(pkg)


from pathlib import Path
import torch
import whisper
import time

input_dir = Path('input')
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
    """Transcribe a single MP3 file locally using Whisper."""
    result = model.transcribe(str(mp3_path))
    return result['text']

def save_transcription_md(text: str) -> Path:
    output_path = output_dir / '02_transcription.md'
    header = '# Transcription completed\n\n'
    output_path.write_text(header + text.strip() + '\n', encoding='utf-8')
    return output_path


# Main execution
start_time = time.time()
mp3_files = sorted(input_dir.glob('*.mp3'))

if not mp3_files:
    print('No MP3 files found in the input folder. Add a single MP3 file to the input/ folder and rerun.')
elif len(mp3_files) > 1:
    print('More than one MP3 file was found. Please keep only one MP3 file in the input/ folder.')
    print('Found files:')
    for mp3_file in mp3_files:
        print(f'  - {mp3_file.name}')
else:
    mp3_file = mp3_files[0]
    print(f'Processing: {mp3_file.name}')
    transcription_text = transcribe_mp3_file(mp3_file)
    saved_path = save_transcription_md(transcription_text)
    print(f'  Saved markdown: {saved_path}')

end_time = time.time()
elapsed_time = end_time - start_time
print(f'Time taken to run the code: {elapsed_time / 60:.2f} minutes')
