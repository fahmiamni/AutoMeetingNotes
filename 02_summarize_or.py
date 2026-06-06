import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

output_dir = Path('output')
input_file = output_dir / '02_transcription.md'
obsidian_dir = Path(r'C:\Users\ASUS\Documents\famb vault')

api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    raise SystemExit(
        "Error: OPENROUTER_API_KEY not found.\n\n"
        "Set it before running, for example:\n"
        "  $env:OPENROUTER_API_KEY='your_api_key_here'\n"
        "  .\\.venv312\\Scripts\\python.exe 02_summarize_or.py"
    )

if not input_file.is_file():
    raise SystemExit(f"No transcription file found at {input_file}.")

content = input_file.read_text(encoding='utf-8')

api_url = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')

#model_name = os.getenv('OPENROUTER_MODEL', 'openai/gpt-5.5')
model_name = os.getenv('OPENROUTER_MODEL', 'google/gemini-3-flash-preview')
#model_name = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-v4-flash')
#model_name = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat')
#model_name = os.getenv('OPENROUTER_MODEL', 'minimax/minimax-m2.7')

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


def find_original_transcription_path() -> Path | None:
    excluded_names = {'02_transcription.md', '05_summarize.md'}
    candidates = [
        path for path in output_dir.glob('*.md')
        if path.name not in excluded_names and not path.stem.endswith('_summary')
    ]

    sorted_candidates = sorted(
        candidates,
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    for path in sorted_candidates:
        try:
            if path.read_text(encoding='utf-8') == content:
                return path
        except OSError:
            continue

    return sorted_candidates[0] if sorted_candidates else None


def safe_filename_part(value: str) -> str:
    return ''.join(char if char.isalnum() or char in ('-', '_', '.') else '_' for char in value)


start_time = time.time()
print(f"Summarizing full transcript with {model_name}...")
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

output_file = output_dir / '05_summarize.md'
original_transcription_path = find_original_transcription_path()
timestamp_prefix = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
safe_model_name = safe_filename_part(model_name)
base_name = original_transcription_path.stem if original_transcription_path else input_file.stem
original_name_output_path = (
    output_dir / f'{original_transcription_path.stem}_summary.md'
    if original_transcription_path
    else None
)
obsidian_output_path = obsidian_dir / f'{timestamp_prefix}_{base_name}_summary_{safe_model_name}.md'

output_dir.mkdir(parents=True, exist_ok=True)
obsidian_dir.mkdir(parents=True, exist_ok=True)
output_file.write_text(summary, encoding='utf-8')
if original_name_output_path:
    original_name_output_path.write_text(summary, encoding='utf-8')
obsidian_output_path.write_text(summary, encoding='utf-8')

print(f"Summary generated with {model_name} and saved to {output_file}")
if original_name_output_path:
    print(f"Summary also saved with original file name: {original_name_output_path}")
print(f"Summary also saved to Obsidian vault: {obsidian_output_path}")

elapsed_time = time.time() - start_time
print(f"Time taken to run the code (summarization): {elapsed_time / 60:.2f} minutes")
