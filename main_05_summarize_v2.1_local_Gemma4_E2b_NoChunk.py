import os
import importlib.util
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoProcessor

# Input and output paths
output_dir = Path('output')
input_file = output_dir / '02_transcription.md'

# Read the transcription content
if not input_file.is_file():
    print(f"No transcription file found at {input_file}.")
    exit(1)

with input_file.open('r', encoding='utf-8') as f:
    content = f.read()

max_new_tokens = int(os.getenv("SUMMARY_MAX_NEW_TOKENS", "500"))

# Load Gemma 4 E2B instruction model.
#
# Default to the local Hugging Face cache because this script is meant for local
# summarization and Hugging Face DNS/network failures can otherwise stop startup
# while checking optional files such as chat_template.json.
model_name = os.getenv("HF_MODEL_ID", "google/gemma-4-E2B-it")
local_files_only = os.getenv("HF_LOCAL_FILES_ONLY", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}

load_kwargs = {"local_files_only": local_files_only}

try:
    processor = AutoProcessor.from_pretrained(model_name, **load_kwargs)
except Exception as exc:
    mode = "local cache" if local_files_only else "Hugging Face"
    raise SystemExit(
        f"Could not load processor for {model_name!r} from {mode}.\n\n"
        "If the model is already downloaded, keep HF_LOCAL_FILES_ONLY=1.\n"
        "If you need to download/update it, connect to the internet and run:\n"
        "  $env:HF_LOCAL_FILES_ONLY='0'; python summarizer_v4_Gemma4_E2b.py\n\n"
        f"Original error: {type(exc).__name__}: {exc}"
    ) from exc

device = os.getenv("HF_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
use_device_map_auto = os.getenv("HF_DEVICE_MAP_AUTO", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}

if use_device_map_auto:
    if not importlib.util.find_spec("accelerate"):
        raise SystemExit(
            "HF_DEVICE_MAP_AUTO=1 requires the 'accelerate' package. "
            "Install accelerate or unset HF_DEVICE_MAP_AUTO."
        )

    print(
        "Loading with device_map='auto'. If generation fails with a meta-device "
        "tensor error, unset HF_DEVICE_MAP_AUTO so the model loads on one device."
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype="auto",
        device_map="auto",
        **load_kwargs,
    )
    input_device = next(
        param.device for param in model.parameters() if param.device.type != "meta"
    )
else:
    print(f"Loading model on {device}.")
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype="auto",
            **load_kwargs,
        ).to(device)
    except RuntimeError as exc:
        if device == "cuda" and "out of memory" in str(exc).lower():
            raise SystemExit(
                "CUDA ran out of memory while loading the model.\n\n"
                "Try running on CPU instead:\n"
                "  $env:HF_DEVICE='cpu'; python summarizer_v4_Gemma4_E2b.py\n\n"
                "Or use a model/device with enough context memory for the full transcript."
            ) from exc
        raise
    input_device = torch.device(device)


def generate_summary(prompt: str, token_budget: int) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You summarize meeting transcripts into clear Markdown notes. "
                "Include concise key points, decisions, and action items when present. "
                "Use plain ASCII Markdown with no emoji."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = processor(text=text, return_tensors="pt").to(input_device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=token_budget,
            do_sample=False,
            pad_token_id=processor.tokenizer.eos_token_id,
        )

    result = processor.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
    del inputs, outputs
    if input_device.type == "cuda":
        torch.cuda.empty_cache()
    return result


def find_original_transcription_path() -> Path | None:
    """Find the original-name transcript saved beside 02_transcription.md."""
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


print(f"Summarizing full transcript with {model_name}...")
summary = generate_summary(
    "Summarize this full meeting transcript into clean Markdown notes.\n\n"
    "Include these sections when information is present:\n"
    "- Key discussion points\n"
    "- Decisions\n"
    "- Action items with owners and deadlines\n"
    "- Important names, fields, prospects, clients, or locations\n\n"
    f"Transcript:\n\n{content}",
    max_new_tokens,
)

# Save the summary to output directory
output_file = output_dir / '05_summarize.md'
original_transcription_path = find_original_transcription_path()
original_name_output_path = (
    output_dir / f'{original_transcription_path.stem}_summary.md'
    if original_transcription_path
    else None
)

output_dir.mkdir(parents=True, exist_ok=True)
output_file.write_text(summary, encoding='utf-8')
if original_name_output_path:
    original_name_output_path.write_text(summary, encoding='utf-8')

print(f"Summary generated and saved to {output_file}")
if original_name_output_path:
    print(f"Summary also saved with original file name: {original_name_output_path}")
