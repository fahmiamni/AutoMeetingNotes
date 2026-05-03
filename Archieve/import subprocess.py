import subprocess
import sys

def run_script(script_path):
    """Run another Python script as a subprocess."""
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, check=True)
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
    success = run_script("main_02_transcribe.py")
    if success:
        print("Transcription completed successfully!")
        
        # Then run the summarization script
        success = run_script("main_05_summarize.py")
        if success:
            print("Summarization completed successfully!")