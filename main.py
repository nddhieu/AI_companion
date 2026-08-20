import os
import sys
import time
import socket
import threading
import multiprocessing
import webbrowser
import urllib.request
from pathlib import Path

# Enable multiprocessing freeze support for PyInstaller Windows binaries
multiprocessing.freeze_support()

# Safely configure standard output and error streams for Windows encoding
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import uvicorn
import uvicorn.logging
import uvicorn.loops
import uvicorn.protocols
from server import app

def find_available_port(start_port=8000, max_attempts=20) -> int:
    """Finds the first available TCP port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    return start_port

PORT = find_available_port(8000)
SERVER_URL = f"http://127.0.0.1:{PORT}"

def start_server(port: int):
    try:
        # log_config=None prevents PyInstaller dictConfig 'Unable to configure formatter default' error
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_config=None,
            log_level="warning"
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        log_path = (Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent) / "error.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"Server startup error on port {port}: {e}\n")

def wait_for_server(port: int, timeout: float = 15.0) -> bool:
    """Polls the local server until it actively responds with HTTP 200 OK."""
    start_time = time.time()
    url = f"http://127.0.0.1:{port}/api/users"
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OmniHealthCheck"})
            with urllib.request.urlopen(req, timeout=0.8) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False

def main():
    print("=" * 60)
    print(f"  * Starting Omni - AI Life Companion *")
    print(f"  URL: {SERVER_URL}")
    print("=" * 60)

    # Start FastAPI server in background thread on available port
    server_thread = threading.Thread(target=start_server, args=(PORT,), daemon=True)
    server_thread.start()

    # Actively wait until the server is 100% ready before opening the window
    print(f"Waiting for backend server to become ready on port {PORT}...")
    ready = wait_for_server(PORT, timeout=15.0)
    if not ready:
        print("Warning: Backend server took longer than expected to report ready.")

    # Try launching native desktop GUI with pywebview if available
    try:
        import webview
        print("Launching native desktop window via WebView2...")
        window = webview.create_window(
            title="Omni — AI Life Companion",
            url=SERVER_URL,
            width=1280,
            height=880,
            min_size=(900, 650),
            background_color="#080c14"
        )
        webview.start()
    except Exception as e:
        print(f"Opening in default browser (fallback: {e})...")
        webbrowser.open(SERVER_URL)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down AI Life Companion...")

if __name__ == "__main__":
    main()


