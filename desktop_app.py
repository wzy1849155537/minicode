"""MiniCode desktop app — native Windows window wrapping the Streamlit UI."""

import os
import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v and v != "your-key-here":
                    os.environ[k] = v


def find_free_port(start=8502):
    import socket
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 8502


def main():
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run",
         str(PROJECT_ROOT / "web" / "app.py"),
         "--server.port", str(port),
         "--server.headless", "true",
         "--server.address", "127.0.0.1",
         "--browser.gatherUsageStats", "false",
         "--global.developmentMode", "false"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
    )

    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    try:
        import webview
        webview.create_window(
            title="MiniCode - AI 编程助手",
            url=url, width=1200, height=800,
            min_size=(900, 600), resizable=True,
        )
        webview.start(debug=False)
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
