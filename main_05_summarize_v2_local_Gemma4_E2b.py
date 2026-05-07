import os
import importlib.util
import torch
from transformers import AutoModelForCausalLM, AutoProcessor

# Input and output paths
input_file = os.path.join('output', '02_transcription.md')
output_dir = 'output'

# Read the transcription content
if not os.path.isfile(input_file):
    print(f"No transcription file found at {input_file}.")
    exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Long prompts can exceed a 6 GB GPU because attention memory grows quickly.
# Summarize in chunks first, then summarize those chunk notes into the final file.
chunk_chars = int(os.getenv("SUMMARY_CHUNK_CHARS", "8000"))
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
                "Or reduce input size with, for example:\n"
                "  $env:MAX_INPUT_CHARS='20000'; python summarizer_v4_Gemma4_E2b.py"
            ) from exc
        raise
    input_device = torch.device(device)

def split_text(text: str, size: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            split_at = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if split_at > start + size // 2:
                end = split_at + 1
        chunks.append(text[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


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


chunks = split_text(content, chunk_chars)
if len(chunks) == 1:
    summary = generate_summary(
        f"Summarize these meeting notes:\n\n{content}",
        max_new_tokens,
    )
else:
    print(f"Transcript split into {len(chunks)} chunks of about {chunk_chars} characters.")
    chunk_summaries = []
    for index, chunk in enumerate(chunks, start=1):
        print(f"Summarizing chunk {index}/{len(chunks)}...")
        chunk_summaries.append(
            generate_summary(
                "Summarize this transcript chunk. Keep names, decisions, "
                f"field/prospect names, and action items:\n\n{chunk}",
                max_new_tokens,
            )
        )

    combined_notes = "\n\n".join(
        f"## Chunk {index}\n{chunk_summary}"
        for index, chunk_summary in enumerate(chunk_summaries, start=1)
    )
    summary = generate_summary(
        "Combine these chunk summaries into one clean Markdown meeting summary. "
        "Include sections for key discussion points, decisions, and action items:\n\n"
        f"{combined_notes}",
        1000,
    )

# Save the summary to output directory
output_filename = '05_summarize.md'
output_file = os.path.join(output_dir, output_filename)
os.makedirs(output_dir, exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(summary)

print(f"Summary generated and saved to {output_file}")
