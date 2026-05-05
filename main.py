from pathlib import Path
import os
import subprocess
import sys
import time


def get_file_name():
    # Get the file name
    input_dir = Path('input')

    # Get all files in the input directory
    files = list(input_dir.glob('*'))

    filename = files[0].name
    return filename
def run_script(script_path):
    """Run another Python script as a subprocess."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            env=env,
        )
        print("Script output:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        print(f"Error output: {e.stderr}")
        return False

# Example usage
if __name__ == "__main__":
    # Run the transcription script
    run_script("main_02_transcribe.py")
    #run_script("main_05_summarize_v1_API_Gpt4o_mini.py")
    run_script("main_05_summarize_v2_local_Gemma4_E2b.py")


    print("-" * 50)

    # Get the file name
    print(get_file_name())
    print("-" * 50)
