@echo off

:: Change directory to where main.py is located
cd /d "D:\GitHub\Active\AutoMeetingNotes"

:: Run using venv Python directly (bypass broken activate.bat)
"D:\11 Projects\_shared\venv_312\Scripts\python.exe" main.py

pause
