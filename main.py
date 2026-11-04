import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


SUPPORTED_AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.ogg', '.mp4')
PROCESSED_TRACKER = Path('output/.processed_files.json')
BATCH_MANIFEST = Path('output/.batch_manifest.json')


def run_step(script_name: str, extra_env: dict[str, str] | None = None) -> None:
    """Run each pipeline step in a fresh process so GPU memory is released."""
    print(f"Running {script_name}...")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    subprocess.run([sys.executable, script_name], check=True, env=env)


def load_processed_files() -> set[str]:
    if not PROCESSED_TRACKER.is_file():
        return set()
    try:
        return set(json.loads(PROCESSED_TRACKER.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return set()


def has_pending_batch() -> bool:
    if not BATCH_MANIFEST.is_file():
        return False
    return bool(json.loads(BATCH_MANIFEST.read_text(encoding="utf-8")))


def run_watcher() -> None:
    input_dir = Path(os.getenv("INPUT_DIR", "input"))
    poll_seconds = float(os.getenv("WATCH_POLL_SECONDS", "5"))
    stable_seconds = float(os.getenv("WATCH_STABLE_SECONDS", "10"))
    if poll_seconds <= 0 or stable_seconds <= 0:
        raise ValueError("WATCH_POLL_SECONDS and WATCH_STABLE_SECONDS must be greater than zero.")

    observed_files: dict[str, tuple[tuple[int, int], float]] = {}
    print(
        f"Watching {input_dir} for new audio files "
        f"(poll every {poll_seconds:g}s; stable for {stable_seconds:g}s).",
        flush=True,
    )

    while True:
        if has_pending_batch():
            run_step("02_summarize_or.py")
            continue

        processed_files = load_processed_files()
        candidates = sorted(
            file
            for extension in SUPPORTED_AUDIO_EXTENSIONS
            for file in input_dir.glob(f"*{extension}")
            if file.name not in processed_files
        )
        candidate_names = {file.name for file in candidates}
        observed_files = {
            name: state for name, state in observed_files.items()
            if name in candidate_names
        }

        now = time.monotonic()
        all_stable = bool(candidates)
        for audio_file in candidates:
            try:
                stat = audio_file.stat()
            except FileNotFoundError:
                all_stable = False
                continue

            signature = (stat.st_size, stat.st_mtime_ns)
            previous = observed_files.get(audio_file.name)
            if previous is None or previous[0] != signature:
                observed_files[audio_file.name] = (signature, now)
                all_stable = False
            elif now - previous[1] < stable_seconds:
                all_stable = False

        if all_stable:
            filenames = [file.name for file in candidates]
            run_step(
                "01_transcribe.py",
                {"TRANSCRIBE_ONLY_FILES": json.dumps(filenames)},
            )
            if has_pending_batch():
                run_step("02_summarize_or.py")

        time.sleep(poll_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the meeting-notes pipeline.")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep running and process new audio files as they arrive.",
    )
    args = parser.parse_args()

    if args.watch:
        run_watcher()
    else:
        run_step("01_transcribe.py")
        run_step("02_summarize_or.py")

