@echo off

:: Use CALL to run the activation 
call .venv312\Scripts\activate

:: Run the  code by sequence
python main_02_transcribe.py
python main_05_summarize.py
 

pause