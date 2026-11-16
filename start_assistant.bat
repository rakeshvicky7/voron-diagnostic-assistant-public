@echo off
rem Starts the Voron 0.2 diagnostic assistant and opens it in the browser.
rem For the full mode, start the Ollama app first. Without Ollama it still works (symptom graph only).
cd /d "%~dp0"
py -3.12 -m src.assistant_v2.server --open
pause
