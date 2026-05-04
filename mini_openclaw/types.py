from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class InboundMessage:
    id: str
    channel: str
    sender: str
    text: str
    session_id: str
    created_at: str


@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    output: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
        }


@dataclass(frozen=True)
class AgentReply:
    text: str
    tool_calls: tuple[ToolResult, ...] = ()


@dataclass(frozen=True)
class OutboundMessage:
    id: str
    channel: str
    target: str
    text: str
    session_id: str
    created_at: str
    tool_calls: tuple[ToolResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel,
            "target": self.target,
            "text": self.text,
            "sessionId": self.session_id,
            "createdAt": self.created_at,
            "toolCalls": [tool_call.to_dict() for tool_call in self.tool_calls],
        }


@dataclass(frozen=True)
class MemoryEntry:
    role: str
    text: str
    at: str


@dataclass(frozen=True)
class SessionState:
    id: str
    messages: tuple[MemoryEntry, ...]
    notes: tuple[str, ...]

    @property
    def session_id(self) -> str:
        return self.id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "messages": [
                {"role": message.role, "text": message.text, "at": message.at}
                for message in self.messages
            ],
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class GatewayEvent:
    type: str
    at: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "at": self.at,
            "payload": _jsonable(self.payload),
        }


@dataclass(frozen=True)
class Delivery:
    channel: str
    target: str
    message: OutboundMessage

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "target": self.target,
            "message": self.message.to_dict(),
        }


class ChannelAdapter(Protocol):
    name: str

    def start(self, gateway: Any) -> None:
        ...

    def stop(self) -> None:
        ...

    def send(self, message: OutboundMessage, target: str) -> None:
        ...


ToolHandler = Callable[[Any, "ToolContext"], Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler


@dataclass(frozen=True)
class ToolContext:
    session_id: str
    message: InboundMessage
    memory: Any


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
