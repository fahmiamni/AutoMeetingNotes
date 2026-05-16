import subprocess
import sys
import os
from pathlib import Path


def run_step(script_name: str, args: list[str] = None) -> None:
    """Run each pipeline step in a fresh process so GPU memory is released."""
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    print(f"Running {script_name} {' '.join(args) if args else ''}...")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(cmd, check=True, env=env)


def copy_new_files_from_gdrive(gdrive_dir: Path, input_dir: Path) -> list[Path]:
    """Copy new MP3 files from GDrive to input folder."""
    input_dir.mkdir(parents=True, exist_ok=True)
    
    gdrive_files = {f.name: f for f in gdrive_dir.glob('*.mp3')}
    input_files = {f.name for f in input_dir.glob('*.mp3')}
    
    new_files = []
    for name, gdrive_path in gdrive_files.items():
        if name in input_files:
            print(f"  Skipping (already in input): {name}")
        else:
            dest = input_dir / name
            print(f"  Copying: {name}")
            dest.write_bytes(gdrive_path.read_bytes())
            new_files.append(dest)
    
    return new_files


if __name__ == '__main__':
    gdrive_dir = Path(r'G:\My Drive')
    input_dir = Path('input')
    
    print("=" * 60)
    print("STEP 1: Copy new MP3 files from GDrive to input folder")
    print("=" * 60)
    new_files = copy_new_files_from_gdrive(gdrive_dir, input_dir)
    
    if not new_files:
        print("No new files to process.")
    else:
        print(f"\nFound {len(new_files)} new file(s)")
        
        print("\n" + "=" * 60)
        print("STEP 2: Transcribe new files")
        print("=" * 60)
        run_step("main_02_transcribe_batch.py", ['--new-only'])
        
        print("\n" + "=" * 60)
        print("STEP 3: Summarize new files")
        print("=" * 60)
        run_step("main_05_summarize_batch.py", ['--new-only'])
        
        print("\n" + "=" * 60)
        print("Batch processing completed!")
        print("=" * 60)


