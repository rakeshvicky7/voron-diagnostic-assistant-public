@echo off
rem Starts the assistant and makes a temporary public web link to it (Cloudflare quick tunnel, free, no account).
rem Send the https://....trycloudflare.com link shown below to your professor.
rem The link works only while this window and the assistant window stay open. Close both to stop.
cd /d "%~dp0"

where cloudflared >nul 2>nul
if errorlevel 1 (
  echo cloudflared is not installed. Install it once with:
  echo     winget install --id Cloudflare.cloudflared
  echo then close this window and start this file again.
  pause
  exit /b
)

rem Visitors must not teach the assistant: confirmed cases are not saved during the demo.
set FMEA_NO_LEARN=1
start "Voron assistant (keep open)" cmd /k py -3.12 -m src.assistant_v2.server
echo Waiting for the assistant to start ...
timeout /t 10 >nul

echo.
echo Look for the line with  https://....trycloudflare.com  below and send that link.
echo.
cloudflared tunnel --url http://localhost:8900
pause
