import subprocess
import sys
import os


def run_step(script_name: str) -> None:
    """Run each pipeline step in a fresh process so GPU memory is released."""
    print(f"Running {script_name}...")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, script_name], check=True, env=env)


print("=" * 60)
print("BATCH PROCESSING: All MP3 files in G:\\My Drive")
print("=" * 60)

run_step("main_02_transcribe_batch.py")
run_step("main_05_summarize_batch.py")

print("=" * 60)
print("Batch processing completed!")
print("=" * 60)


