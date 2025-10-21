import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen
from urllib.error import URLError


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server API)
        if self.path in ("/", "/health", "/ping"):
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    # Silence default logging to stderr
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def start_keepalive_server() -> threading.Thread:
    """Start a lightweight HTTP server for uptime/health checks.

    Binds to host from KEEPALIVE_HOST (default 0.0.0.0) and port from
    PORT (common on free PaaS) or KEEPALIVE_PORT (fallback 8080).
    Returns the background Thread instance (daemon).
    """
    host = os.getenv("KEEPALIVE_HOST", "0.0.0.0")
    port_env = os.getenv("PORT") or os.getenv("KEEPALIVE_PORT")
    try:
        port = int(port_env) if port_env else 8080
    except ValueError:
        port = 8080

    httpd = HTTPServer((host, port), _HealthHandler)

    def _serve():
        try:
            httpd.serve_forever(poll_interval=0.5)
        except Exception:
            # Let the main process continue even if server stops unexpectedly
            pass

    t = threading.Thread(target=_serve, name="keepalive-http", daemon=True)
    t.start()
    return t


def start_self_ping(url: str, interval_seconds: int = 300) -> threading.Thread:
    """Start a background thread that pings the given URL periodically.

    Useful to keep free hosting platforms warm. If the request fails,
    it silently retries on the next interval.
    """

    def _loop():
        # Small initial delay to allow the app to bind the port
        time.sleep(5)
        while True:
            try:
                with urlopen(url, timeout=10) as resp:
                    # Drain response to let the server count the hit
                    resp.read(64)
            except URLError:
                pass
            except Exception:
                # Never crash the thread
                pass
            time.sleep(max(30, int(interval_seconds)))

    t = threading.Thread(target=_loop, name="keepalive-ping", daemon=True)
    t.start()
    return t

