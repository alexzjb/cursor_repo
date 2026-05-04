import json
import unittest
import urllib.error
import urllib.request

from mini_openclaw import create_default_gateway
from mini_openclaw.server import create_gateway_server


def post_json(url: str, payload: dict):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class MiniOpenClawTest(unittest.TestCase):
    def test_gateway_remembers_session_notes(self):
        gateway = create_default_gateway(clock=lambda: "2026-05-04T14:49:00Z")

        first = gateway.receive(channel="console", sender="alice", text="/remember ship the checklist")
        second = gateway.receive(channel="console", sender="alice", text="what now?")

        self.assertEqual(first.text, "Remembered: ship the checklist")
        self.assertIn('You said: "what now?".', second.text)
        self.assertIn("I remember: ship the checklist.", second.text)
        self.assertEqual(len(gateway.sessions()[0].messages), 4)

    def test_tool_calls_are_recorded_and_rendered(self):
        gateway = create_default_gateway(clock=lambda: "2026-05-04T14:49:00Z")

        reply = gateway.receive(channel="console", sender="alice", text="/tool time")

        self.assertEqual(reply.text, 'Tool "time" returned:\n2026-05-04T14:49:00Z')
        self.assertEqual(reply.tool_calls[0].name, "time")
        self.assertTrue(reply.tool_calls[0].ok)

    def test_calc_tool_evaluates_safe_arithmetic(self):
        gateway = create_default_gateway(clock=lambda: "2026-05-04T14:49:00Z")

        reply = gateway.receive(channel="console", sender="alice", text='/tool calc {"expr":"1 + 2 * 3"}')

        self.assertEqual(reply.text, 'Tool "calc" returned:\n7')

    def test_gateway_tracks_deliveries_and_events(self):
        gateway = create_default_gateway(clock=lambda: "2026-05-04T14:49:00Z")
        events = []
        gateway.on_event(events.append)

        reply = gateway.receive(channel="webhook", sender="chat-1", text="/status")

        self.assertIn("MiniClaw online", reply.text)
        self.assertEqual(gateway.deliveries()[0].target, "chat-1")
        self.assertEqual(events[-1].type, "message.processed")

    def test_http_server_message_and_session_endpoints(self):
        gateway = create_default_gateway(clock=lambda: "2026-05-04T14:49:00Z")
        server = create_gateway_server(host="127.0.0.1", port=0, gateway=gateway)
        self.assertIsNotNone(server.url)

        try:
            health = get_json(f"{server.url}/health")
            message = post_json(
                f"{server.url}/message",
                {"channel": "webhook", "from": "alice", "text": "/remember local first"},
            )
            sessions = get_json(f"{server.url}/sessions")
        finally:
            server.stop()

        self.assertEqual(health, {"ok": True, "name": "mini-openclaw"})
        self.assertEqual(message["reply"]["text"], "Remembered: local first")
        self.assertEqual(sessions["sessions"][0]["notes"], ["local first"])

    def test_http_server_rejects_bad_payloads(self):
        server = create_gateway_server(host="127.0.0.1", port=0, gateway=create_default_gateway())
        self.assertIsNotNone(server.url)

        try:
            request = urllib.request.Request(
                f"{server.url}/message",
                data=json.dumps({"text": "missing channel"}).encode("utf-8"),
                headers={"content-type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=5)
            body = json.loads(raised.exception.read().decode("utf-8"))
        finally:
            server.stop()

        self.assertEqual(raised.exception.code, 400)
        self.assertIn("channel", body["error"])


if __name__ == "__main__":
    unittest.main()
