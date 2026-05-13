import subprocess
import sys
import os


def run_step(script_name: str) -> None:
    """Run each pipeline step in a fresh process so GPU memory is released."""
    print(f"Running {script_name}...")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, script_name], check=True, env=env)


run_step("main_02_transcribe_v4_ProcessLatest.py")
#run_step("main_05_summarize_v2.1_local_Gemma4_E2b_NoChunk.py")
#run_step("main_05_summarize_v3.1_API_DeepseekCheap_NoChunk.py")
run_step("main_05_summarize_v4_openrouter.py")

