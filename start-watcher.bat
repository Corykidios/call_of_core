@echo off
REM ── Call of Core — Windows auto-start helper ───────────────────────────────
REM Drop this file in:
REM   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
REM
REM Edit the two paths below to match your Python installation and
REM wherever you cloned this repo.
REM ─────────────────────────────────────────────────────────────────────────────

set PYTHON=C:\Users\YourName\AppData\Local\Python\pythoncore-3.14-64\python.exe
set WATCHER=C:\path\to\call_of_core\mp-watcher.py

start "" "%PYTHON%" "%WATCHER%"
