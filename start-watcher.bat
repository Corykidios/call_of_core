@echo off
REM ── Call of Core — Windows auto-start helper ───────────────────────────────
REM Drop this file in:
REM   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
REM
REM Set MEMORY_PLUGIN_TOKEN as a Windows environment variable (preferred),
REM or uncomment and fill in the line below (less secure).
REM ─────────────────────────────────────────────────────────────────────────────

set PYTHON=C:\Users\YourName\AppData\Local\Python\pythoncore-3.14-64\python.exe
set WATCHER=C:\path\to\call_of_core\mp-watcher.py

REM Uncomment this line if you are not using a system environment variable:
REM set MEMORY_PLUGIN_TOKEN=your_token_here

if "%MEMORY_PLUGIN_TOKEN%"=="" (
    echo ERROR: MEMORY_PLUGIN_TOKEN is not set. The watcher will not start.
    pause
    exit /b 1
)

start "" "%PYTHON%" "%WATCHER%"
