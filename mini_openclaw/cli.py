from __future__ import annotations

import argparse
import json
import sys

from .gateway import create_default_gateway
from .server import GatewayHTTPServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini-openclaw", description="Run a tiny local-first assistant gateway.")
    subcommands = parser.add_subparsers(dest="command")

    send = subcommands.add_parser("send", help="Process one message and print the reply.")
    send.add_argument("--message", "-m", required=True)
    send.add_argument("--user", default="local-user")
    send.add_argument("--channel", default="console")

    chat = subcommands.add_parser("chat", help="Start an interactive console channel.")
    chat.add_argument("--user", default="local-user")

    serve = subcommands.add_parser("serve", help="Start the HTTP gateway.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=18789)

    subcommands.add_parser("doctor", help="Print local gateway diagnostics.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gateway = create_default_gateway()

    if args.command == "send":
        reply = gateway.receive(channel=args.channel, sender=args.user, text=args.message)
        print(reply.text)
        return 0

    if args.command == "chat":
        print("MiniClaw chat started. Type /help or /exit.")
        while True:
            try:
                text = input("> ")
            except EOFError:
                print()
                return 0
            if text.strip() == "/exit":
                return 0
            reply = gateway.receive(channel="console", sender=args.user, text=text)
            print(reply.text)

    if args.command == "serve":
        server = GatewayHTTPServer(gateway=gateway)
        server.start(args.host, args.port)
        print(f"MiniClaw Gateway listening at {server.url}")
        try:
            server.wait_forever()
        except KeyboardInterrupt:
            server.stop()
        return 0

    if args.command == "doctor":
        print(json.dumps(gateway.doctor(), indent=2))
        return 0

    build_parser().print_help(sys.stderr)
    return 2
