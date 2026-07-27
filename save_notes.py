import os
from pathlib import Path

import markdown
import requests
from dotenv import load_dotenv


load_dotenv()

OBSIDIAN_VAULT = Path(r'C:\Users\ASUS\Documents\famb vault')
MATON_BASE_URL = 'https://api.maton.ai'


def _maton_headers() -> dict:
    api_key = os.getenv('MATON_API_KEY')
    if not api_key:
        raise SystemExit(
            "Error: MATON_API_KEY not found.\n"
            "Set it in .env or as an environment variable."
        )
    return {
        'Authorization': f'Bearer {api_key}',
    }


def _resolve_section_id() -> str:
    """Resolve ONENOTE_NOTEBOOK_NAME + ONENOTE_SECTION_NAME to a section ID."""
    notebook_name = os.getenv('ONENOTE_NOTEBOOK_NAME', '')
    section_name = os.getenv('ONENOTE_SECTION_NAME', '')

    if not notebook_name or not section_name:
        raise SystemExit(
            "Error: ONENOTE_NOTEBOOK_NAME and ONENOTE_SECTION_NAME must be set.\n"
            "Set them in .env or as environment variables."
        )

    headers = _maton_headers()

    # List notebooks
    resp = requests.get(
        f'{MATON_BASE_URL}/one-note/v1.0/me/onenote/notebooks',
        headers=headers,
        timeout=30,
    )
    if resp.status_code != 200:
        raise SystemExit(f"Maton API error listing notebooks {resp.status_code}: {resp.text}")

    notebooks = resp.json().get('value', [])
    notebook = next((n for n in notebooks if n['displayName'] == notebook_name), None)
    if not notebook:
        available = [n['displayName'] for n in notebooks]
        raise SystemExit(
            f"Notebook '{notebook_name}' not found.\n"
            f"Available notebooks: {available}"
        )

    # List sections in the notebook (use Maton gateway URL, not raw Graph URL)
    notebook_id = notebook.get('id', '')
    sections_url = f'{MATON_BASE_URL}/one-note/v1.0/me/onenote/notebooks/{notebook_id}/sections'
    resp = requests.get(sections_url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise SystemExit(f"Maton API error listing sections {resp.status_code}: {resp.text}")

    sections = resp.json().get('value', [])
    section = next((s for s in sections if s['displayName'] == section_name), None)
    if not section:
        available = [s['displayName'] for s in sections]
        raise SystemExit(
            f"Section '{section_name}' not found in notebook '{notebook_name}'.\n"
            f"Available sections: {available}"
        )

    return section['id']


def _markdown_to_onenote_html(title: str, md_content: str) -> str:
    """Convert markdown content to OneNote-compatible HTML."""
    body_html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    return (
        '<!DOCTYPE html>\n'
        '<html>\n'
        '<head>\n'
        f'<title>{title}</title>\n'
        '</head>\n'
        '<body>\n'
        f'{body_html}\n'
        '</body>\n'
        '</html>'
    )


def save_to_obsidian(content: str, filename_stem: str) -> Path:
    """Save markdown content to Obsidian vault."""
    OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
    output_path = OBSIDIAN_VAULT / f'{filename_stem}.md'
    output_path.write_text(content, encoding='utf-8')
    print(f"  Saved to Obsidian vault: {output_path}")
    return output_path


def save_to_onenote(content: str, title: str) -> str | None:
    """Save markdown content to OneNote via Maton API.

    Returns the page ID on success, None on failure (prints warning).
    """
    try:
        section_id = _resolve_section_id()
        html = _markdown_to_onenote_html(title, content)

        resp = requests.post(
            f'{MATON_BASE_URL}/one-note/v1.0/me/onenote/sections/{section_id}/pages',
            headers={**_maton_headers(), 'Content-Type': 'text/html'},
            data=html.encode('utf-8'),
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            print(f"  Warning: OneNote save failed ({resp.status_code}): {resp.text}")
            return None

        page = resp.json()
        page_id = page.get('id', 'unknown')
        print(f"  Saved to OneNote: {title} (page {page_id})")
        return page_id

    except requests.RequestException as e:
        print(f"  Warning: OneNote save failed (network error): {e}")
        return None
    except SystemExit as e:
        print(f"  Warning: OneNote save failed: {e}")
        return None


def save_notes(
    content: str,
    filename_stem: str,
    save_obsidian: bool = True,
    save_onenote: bool = True,
) -> None:
    """Save meeting notes to configured destinations."""
    if save_obsidian:
        save_to_obsidian(content, filename_stem)
    if save_onenote:
        save_to_onenote(content, filename_stem)
