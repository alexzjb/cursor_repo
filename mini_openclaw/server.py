from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .gateway import OpenClawGateway, create_default_gateway


def create_handler(gateway: OpenClawGateway) -> type[BaseHTTPRequestHandler]:
    events: list[dict[str, Any]] = []

    def remember_event(event: Any) -> None:
        events.append(event.to_dict())
        del events[:-100]

    gateway.on_event(remember_event)

    class Handler(BaseHTTPRequestHandler):
        server: GatewayHTTPServer

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            if self.path == "/health":
                self._send_json(200, {"ok": True, "name": "mini-openclaw"})
                return
            if self.path == "/sessions":
                self._send_json(200, {"sessions": [s.to_dict() for s in gateway.sessions()]})
                return
            if self.path == "/events":
                self._send_json(200, {"events": events})
                return
            self._send_json(404, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            if self.path != "/message":
                self._send_json(404, {"error": "Not found"})
                return

            try:
                payload = self._read_json()
                if not _valid_message(payload):
                    self._send_json(400, {"error": "Expected channel, from, and text strings."})
                    return
                reply = gateway.receive(
                    channel=payload["channel"],
                    sender=payload["from"],
                    text=payload["text"],
                    session_id=payload.get("sessionId"),
                )
                self._send_json(200, {"reply": reply.to_dict()})
            except Exception as exc:  # pragma: no cover - defensive HTTP boundary
                self._send_json(500, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("content-length", "0"))
            if length > 1_000_000:
                raise ValueError("Request body too large")
            raw = self.rfile.read(length).decode("utf-8")
            if not raw.strip():
                return {}
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Expected JSON object")
            return payload

        def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status_code)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _valid_message(payload: dict[str, Any]) -> bool:
    return (
        isinstance(payload.get("channel"), str)
        and isinstance(payload.get("from"), str)
        and isinstance(payload.get("text"), str)
        and (payload.get("sessionId") is None or isinstance(payload.get("sessionId"), str))
    )


class GatewayHTTPServer:
    def __init__(self, gateway: OpenClawGateway | None = None) -> None:
        self.gateway = gateway or create_default_gateway()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.url: str | None = None

    def start(self, host: str = "127.0.0.1", port: int = 18789) -> None:
        self._server = ThreadingHTTPServer((host, port), create_handler(self.gateway))
        actual_host, actual_port = self._server.server_address[:2]
        self.url = f"http://{actual_host}:{actual_port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def serve_forever(self, host: str = "127.0.0.1", port: int = 18789) -> None:
        self._server = ThreadingHTTPServer((host, port), create_handler(self.gateway))
        actual_host, actual_port = self._server.server_address[:2]
        self.url = f"http://{actual_host}:{actual_port}"
        self._server.serve_forever()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None


def create_gateway_server(
    host: str = "127.0.0.1",
    port: int = 18789,
    gateway: OpenClawGateway | None = None,
) -> GatewayHTTPServer:
    server = GatewayHTTPServer(gateway=gateway)
    server.start(host, port)
    return server
