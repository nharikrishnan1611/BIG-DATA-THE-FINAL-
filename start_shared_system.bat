@echo off
title AI Fake News Verification - 4-Person Shared System
echo ======================================================================
echo AI Fake News Detection with Evidence & Source Verification Dashboard
echo Launching server for 4+ users with local and public global access...
echo ======================================================================

echo Starting backend on 0.0.0.0:8000 ...
start /B python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000

timeout /t 2 /nobreak >nul

echo Starting Cloudflare edge tunnel...
start .\cloudflared.exe tunnel --url http://127.0.0.1:8000

echo.
echo ======================================================================
echo Access Links:
echo 1. Local Browser:    http://localhost:8000
echo 2. Same Wi-Fi Link:  http://192.168.1.4:8000
echo 3. Global Edge Link: Check the Cloudflare window for https://...trycloudflare.com
echo ======================================================================
pause
