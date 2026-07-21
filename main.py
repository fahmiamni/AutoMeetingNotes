import subprocess
import sys
import os


def run_step(script_name: str) -> None:
    """Run each pipeline step in a fresh process so GPU memory is released."""
    print(f"Running {script_name}...")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, script_name], check=True, env=env)


run_step("01_transcribe.py")
#run_step("02_summarize_gemma.py")
run_step("02_summarize_or.py")


