@echo off

:: Change directory to where main.py is located
cd /d "D:\GitHub\Active\AutoMeetingNotes"

:: Run using venv Python directly (bypass broken activate.bat)
"D:\GitHub\Active\AutoMeetingNotes\.venv\Scripts\python.exe" main.py
pause
