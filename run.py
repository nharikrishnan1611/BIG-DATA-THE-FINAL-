"""
Launcher for AI Fake News Verification Dashboard.
Runs FastAPI backend and serves the frontend on http://localhost:8000.
"""

import sys
import webbrowser
import threading
import time
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("=" * 70)
    print("AI Fake News Detection with Evidence & Source Verification Dashboard")
    print("=" * 70)
    print("Starting server at http://localhost:8000 and network http://0.0.0.0:8000 ...")
    
    # Open browser automatically in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
