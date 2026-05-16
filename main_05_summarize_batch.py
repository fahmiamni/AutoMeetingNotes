import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

output_dir = Path('output')
obsidian_dir = Path(r'C:\Users\ASUS\Documents\famb vault')

api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    raise SystemExit(
        "Error: OPENROUTER_API_KEY not found.\n\n"
        "Set it before running, for example:\n"
        "  $env:OPENROUTER_API_KEY='your_api_key_here'\n"
        "  .\\.venv312\\Scripts\\python.exe main_05_summarize_batch.py <transcription_file>"
    )

api_url = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')
model_name = os.getenv('OPENROUTER_MODEL', 'minimax/minimax-m2.7')

max_tokens = int(os.getenv('SUMMARY_MAX_TOKENS', '30000'))
timeout_seconds = int(os.getenv('OPENROUTER_TIMEOUT_SECONDS', '180'))


def call_openrouter(prompt: str, token_budget: int) -> str:
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://localhost',
        'X-Title': 'MeetingNotesSummarizer',
    }
    payload = {
        'model': model_name,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You summarize meeting transcripts into clear Markdown notes. '
                    'Include concise key points, decisions, and action items when present. '
                    'Use plain ASCII Markdown with no emoji.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2,
        'max_tokens': token_budget,
        'stream': False,
    }

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        raise SystemExit(f"OpenRouter API error {response.status_code}: {response.text}")

    result = response.json()
    return result['choices'][0]['message']['content'].strip()


def safe_filename_part(value: str) -> str:
    return ''.join(char if char.isalnum() or char in ('-', '_', '.') else '_' for char in value)


def summarize_file(input_path: Path) -> None:
    if not input_path.is_file():
        raise SystemExit(f"Transcription file not found: {input_path}")

    content = input_path.read_text(encoding='utf-8')
    base_name = input_path.stem

    print(f"  Summarizing: {base_name}")

    start_time = time.time()
    summary = call_openrouter(
        "Summarize this full meeting transcript into clean Markdown notes.\n\n"
        "Include these sections when information is present:\n"
        "- Key discussion points\n"
        "- Decisions\n"
        "- Action items with owners and deadlines\n"
        "- Important names, fields, prospects, clients, or locations\n\n"
        f"Transcript:\n\n{content}",
        max_tokens,
    )

    timestamp_prefix = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
    safe_model_name = safe_filename_part(model_name)

    output_file = output_dir / f'{base_name}_summary.md'
    obsidian_output_path = obsidian_dir / f'{timestamp_prefix}_{base_name}_summary_{safe_model_name}.md'

    output_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    output_file.write_text(summary, encoding='utf-8')
    obsidian_output_path.write_text(summary, encoding='utf-8')

    print(f"    Saved: {output_file.name}")
    print(f"    Saved to Obsidian: {obsidian_output_path.name}")

    elapsed_time = time.time() - start_time
    print(f"    Summarization time: {elapsed_time / 60:.2f} minutes")


def get_all_transcription_files(obsidian_dir: Path, new_only: bool = False) -> list[Path]:
    transcription_files = list(output_dir.glob('*.md'))
    transcription_files = [f for f in transcription_files if not f.name.endswith('_summary.md') and f.name != '02_transcription.md' and f.name != '05_summarize.md']
    
    if new_only:
        summarized_stems = {f.stem.replace('_summary', '') for f in output_dir.glob('*_summary.md')}
        unprocessed = [f for f in transcription_files if f.stem not in summarized_stems]
        for f in transcription_files:
            if f.stem in summarized_stems:
                print(f'  Skipping (already summarized): {f.stem}')
        return unprocessed
    
    processed_stems = set()
    if obsidian_dir.exists():
        for f in obsidian_dir.glob('*_summary_*.md'):
            stem = f.stem
            parts = stem.split('_')
            if len(parts) >= 3:
                processed_stems.add('_'.join(parts[1:-1]))
    
    unprocessed = []
    for f in transcription_files:
        if f.stem not in processed_stems:
            unprocessed.append(f)
        else:
            print(f'  Skipping (already summarized): {f.stem}')
    
    return unprocessed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--new-only', action='store_true', help='Only process new files (skip if already summarized)')
    args = parser.parse_args()
    
    unprocessed_files = get_all_transcription_files(obsidian_dir, args.new_only)
    
    if not unprocessed_files:
        print('No unprocessed transcription files found.')
    else:
        print(f'Found {len(unprocessed_files)} unprocessed transcription file(s)')
        
        for transcription_file in unprocessed_files:
            try:
                summarize_file(transcription_file)
            except Exception as e:
                print(f'  Error summarizing {transcription_file.name}: {e}')