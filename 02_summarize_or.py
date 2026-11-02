import os
import re
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from save_notes import save_notes


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

api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    raise SystemExit(
        "Error: OPENROUTER_API_KEY not found.\n\n"
        "Set it before running, for example:\n"
        "  $env:OPENROUTER_API_KEY='your_api_key_here'\n"
        "  .\\.venv312\\Scripts\\python.exe 02_summarize_or.py"
    )

api_url = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')
model_name = os.getenv('OPENROUTER_MODEL', 'google/gemini-3-flash-preview')
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


def safe_filename_part(value: str) -> str:
    return ''.join(char if char.isalnum() or char in ('-', '_', '.') else '_' for char in value)

BATCH_MANIFEST = output_dir / '.batch_manifest.json'


def summarize_transcript(transcript_content: str, source_name: str) -> None:
    """Summarize a single transcript and save outputs."""
    print(f"Summarizing: {source_name} with {model_name}...")
    summary = call_openrouter(
        user_prompt_template.format(transcript=transcript_content),
        max_tokens,
    )

    safe_source = safe_filename_part(Path(source_name).stem)

    output_file = output_latest / '05_summarize.md'
    original_name_output_path = output_summaries / f'{safe_source}_summary.md'

    output_file.write_text(summary, encoding='utf-8')
    original_name_output_path.write_text(summary, encoding='utf-8')

    print(f"  Summary saved to {output_file}")
    print(f"  Summary saved with original name: {original_name_output_path}")

    save_notes(summary, safe_source, save_onenote=True)


start_time = time.time()

if BATCH_MANIFEST.is_file():
    manifest = json.loads(BATCH_MANIFEST.read_text(encoding='utf-8'))
    if manifest:
        print(f"Batch mode: {len(manifest)} transcript(s) to summarize.\n")
        for idx, entry in enumerate(manifest, 1):
            transcript_path = Path(entry['transcript_md'])
            audio_name = entry.get('audio_file', transcript_path.stem)
            if not transcript_path.is_file():
                print(f"  [{idx}/{len(manifest)}] SKIP - transcript not found: {transcript_path}")
                continue
            content = transcript_path.read_text(encoding='utf-8')
            print(f"  [{idx}/{len(manifest)}] {audio_name}")
            summarize_transcript(content, audio_name)
        # Clear the manifest after successful processing
        BATCH_MANIFEST.write_text('[]', encoding='utf-8')
    else:
        print("Batch manifest is empty. Nothing to summarize.")
else:
    # Fallback: single-file mode using latest/02_transcription.md
    input_file = output_latest / '02_transcription.md'
    if not input_file.is_file():
        raise SystemExit(f"No transcription file found at {input_file}.")
    content = input_file.read_text(encoding='utf-8')
    summarize_transcript(content, input_file.name)

elapsed_time = time.time() - start_time
print(f"\nTime taken to run the code (summarization): {elapsed_time / 60:.2f} minutes")
