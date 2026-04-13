"""
Legacy HTTP daemon (Ollama backend).

This was an earlier prototype that served completions over HTTP and delegated
to Ollama. The current Zsh plugin uses a Unix-socket daemon instead:

  python -m model_completer.daemon
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

from model_completer.utils import load_config
from model_completer.ollama_complete import complete

DEFAULT_PORT = 11435


class CompletionHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/complete" and not self.path.startswith("/complete?"):
            self.send_error(404)
            return
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        try:
            command = body.decode("utf-8", errors="replace").strip()
        except Exception:
            command = ""
        if not command:
            self._send("", 400)
            return
        config = load_config()
        url = config.get("ollama", {}).get("url", "http://localhost:11434")
        model = config.get("model", "zsh-assistant")
        timeout = config.get("ollama", {}).get("timeout", 10)
        timeout = min(int(timeout), 5)
        result = complete(command, url, model, timeout=timeout)
        self._send(result or command)

    def do_GET(self):
        if self.path == "/health":
            self._send("ok")
            return
        self.send_error(404)

    def _send(self, text: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # quiet by default


def main():
    port = int(os.environ.get("MODEL_COMPLETION_DAEMON_PORT", DEFAULT_PORT))
    server = HTTPServer(("127.0.0.1", port), CompletionHandler)
    print(
        f"Legacy Ollama daemon listening on http://127.0.0.1:{port}/complete",
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()

