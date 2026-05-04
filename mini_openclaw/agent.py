from __future__ import annotations

import json

from .memory import InMemoryStore
from .tools import ToolRegistry
from .types import AgentReply, InboundMessage, ToolResult


class ClawAgent:
    def __init__(self, memory: InMemoryStore, tools: ToolRegistry, name: str = "MiniClaw") -> None:
        self.memory = memory
        self.tools = tools
        self.name = name

    def handle(self, message: InboundMessage) -> AgentReply:
        self.memory.append(message.session_id, "user", message.text)
        tool_result = self._maybe_run_tool(message)
        text = self._format_tool_reply(tool_result) if tool_result else self._compose_reply(message)
        self.memory.append(message.session_id, "assistant", text)
        return AgentReply(text=text, tool_calls=(tool_result,) if tool_result else ())

    def sessions(self):
        return self.memory.sessions()

    def _compose_reply(self, message: InboundMessage) -> str:
        normalized = message.text.strip()
        lower = normalized.lower()

        if lower == "/help":
            return "\n".join(
                [
                    f"{self.name} supports:",
                    "- /status: inspect the local session",
                    "- /tools: list available host tools",
                    "- /remember <note>: store a note in this session",
                    "- /recall: show remembered notes",
                    "- /tool <name> [json]: run a local tool",
                ]
            )

        if lower == "/status":
            history_count = len(self.memory.history(message.session_id))
            tools = ", ".join(self.tools.names())
            return f"{self.name} online. Session has {history_count} stored messages. Tools: {tools}."

        if lower == "/tools":
            return "Available tools: " + ", ".join(self.tools.names())

        if lower.startswith("/remember "):
            note = normalized[len("/remember ") :].strip()
            if not note:
                return "Tell me what to remember after /remember."
            self.memory.remember(message.session_id, note)
            return f"Remembered: {note}"

        if lower == "/recall":
            notes = self.memory.notes(message.session_id)
            if not notes:
                return "No notes stored in this session yet."
            return "\n".join(["Remembered notes:", *[f"{index + 1}. {note}" for index, note in enumerate(notes)]])

        recent_notes = self.memory.notes(message.session_id)[-2:]
        context = f" I remember: {'; '.join(recent_notes)}." if recent_notes else ""
        return f'You said: "{normalized}".{context} Try /help for commands.'

    def _maybe_run_tool(self, message: InboundMessage) -> ToolResult | None:
        text = message.text.strip()
        if not text.lower().startswith("/tool "):
            return None

        rest = text[len("/tool ") :].strip()
        name, _, raw_args = rest.partition(" ")
        if not name:
            return ToolResult(name="unknown", ok=False, error="Usage: /tool <name> [json]")

        args: object = {}
        if raw_args.strip():
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError as error:
                return ToolResult(name=name, ok=False, error=f"Invalid JSON arguments: {error.msg}")

        return self.tools.run(name, args, message=message, memory=self.memory)

    def _format_tool_reply(self, result: ToolResult) -> str:
        if not result.ok:
            return f'Tool "{result.name}" failed: {result.error}'
        rendered = result.output if isinstance(result.output, str) else json.dumps(result.output, indent=2, sort_keys=True)
        return f'Tool "{result.name}" returned:\n{rendered}'
