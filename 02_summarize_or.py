import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

TEMPLATE_PATH = Path(__file__).parent / 'summarizer_template.md'

DEFAULT_SYSTEM_MESSAGE = (
    'You summarize meeting transcripts into clear Markdown notes. '
    'Include concise key points, decisions, and action items when present. '
    'Use plain ASCII Markdown with no emoji.'
)

DEFAULT_USER_PROMPT = (
    "Summarize this full meeting transcript into clean Markdown notes.\n\n"
    "Include these sections when information is present:\n"
    "- Key discussion points\n"
    "- Decisions\n"
    "- Action items with owners and deadlines\n"
    "- Important names, fields, prospects, clients, or locations\n\n"
    "Transcript:\n\n{transcript}"
)


def load_template() -> tuple[str, str]:
    """Load system message and user prompt from summarizer_template.md.

    Template format:
        <!-- SYSTEM MESSAGE -->
        <system message text>
        ---
        <!-- USER PROMPT -->
        <user prompt text with {transcript} placeholder>

    Falls back to defaults if the template is missing or malformed.
    """
    if not TEMPLATE_PATH.is_file():
        print(f"Warning: Template not found at {TEMPLATE_PATH}, using defaults.")
        return DEFAULT_SYSTEM_MESSAGE, DEFAULT_USER_PROMPT

    raw = TEMPLATE_PATH.read_text(encoding='utf-8')

    parts = raw.split('---', 1)
    if len(parts) != 2:
        print("Warning: Template missing '---' separator, using defaults.")
        return DEFAULT_SYSTEM_MESSAGE, DEFAULT_USER_PROMPT

    system_part = parts[0].strip()
    user_part = parts[1].strip()

    # Strip comment headers like <!-- SYSTEM MESSAGE -->
    system_msg = re.sub(r'<!--.*?-->\s*', '', system_part).strip()
    user_prompt = re.sub(r'<!--.*?-->\s*', '', user_part).strip()

    if not system_msg or '{transcript}' not in user_prompt:
        print("Warning: Template is malformed (missing system message or {transcript} placeholder), using defaults.")
        return DEFAULT_SYSTEM_MESSAGE, DEFAULT_USER_PROMPT

    return system_msg, user_prompt


system_message, user_prompt_template = load_template()
print(f"Loaded summarizer template from {TEMPLATE_PATH}")

output_dir = Path('output')
output_latest = output_dir / 'latest'
output_transcripts = output_dir / 'transcripts'
output_summaries = output_dir / 'summaries'
input_file = output_latest / '02_transcription.md'
output_latest.mkdir(parents=True, exist_ok=True)
output_transcripts.mkdir(parents=True, exist_ok=True)
output_summaries.mkdir(parents=True, exist_ok=True)
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
                'content': system_message,
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
    candidates = [
        path for path in output_transcripts.glob('*.md')
        if not path.stem.endswith('_summary')
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
    user_prompt_template.format(transcript=content),
    max_tokens,
)

output_file = output_latest / '05_summarize.md'
original_transcription_path = find_original_transcription_path()
timestamp_prefix = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
safe_model_name = safe_filename_part(model_name)
base_name = original_transcription_path.stem if original_transcription_path else input_file.stem
original_name_output_path = (
    output_summaries / f'{original_transcription_path.stem}_summary.md'
    if original_transcription_path
    else None
)
obsidian_output_path = obsidian_dir / f'{timestamp_prefix}_{base_name}_summary_{safe_model_name}.md'

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
