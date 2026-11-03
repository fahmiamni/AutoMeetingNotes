@echo off

:: Change directory to where main.py is located
::cd /d "D:\GitHub\Active\AutoMeetingNotes"
cd /d "%~dp0"


:: Run using venv Python directly (bypass broken activate.bat)
::"D:\GitHub\Active\AutoMeetingNotes\.venv\Scripts\python.exe" main.py
"%~dp0.venv\Scripts\python.exe" main.py


pause
