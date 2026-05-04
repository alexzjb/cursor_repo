from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .agent import ClawAgent
from .memory import InMemoryStore
from .tools import ToolRegistry, create_default_tools
from .types import Delivery, GatewayEvent, InboundMessage, OutboundMessage


Clock = Callable[[], str]
EventListener = Callable[[GatewayEvent], None]


class OpenClawGateway:
    def __init__(
        self,
        *,
        agent: ClawAgent | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.agent = agent or create_default_agent(clock=clock)
        self._deliveries: list[Delivery] = []
        self._listeners: list[EventListener] = []
        self._clock = clock or iso_now

    def on_event(self, listener: EventListener) -> None:
        self._listeners.append(listener)

    def receive(
        self,
        *,
        channel: str,
        sender: str,
        text: str,
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> OutboundMessage:
        inbound = InboundMessage(
            id=message_id or f"msg_{uuid4().hex[:10]}",
            channel=channel,
            sender=sender,
            text=text,
            session_id=session_id or f"{channel}:{sender}",
            created_at=self._clock(),
        )
        agent_reply = self.agent.handle(inbound)
        reply = OutboundMessage(
            id=f"out_{uuid4().hex[:10]}",
            channel=channel,
            target=sender,
            text=agent_reply.text,
            session_id=inbound.session_id,
            created_at=self._clock(),
            tool_calls=agent_reply.tool_calls,
        )
        delivery = Delivery(channel=channel, target=sender, message=reply)
        self._deliveries.append(delivery)

        self._emit("message.processed", {"inbound": inbound, "outbound": reply})
        return reply

    def list_sessions(self):
        return self.agent.sessions()

    def sessions(self):
        return self.list_sessions()

    def list_deliveries(self) -> list[Delivery]:
        return list(self._deliveries)

    def deliveries(self) -> list[Delivery]:
        return self.list_deliveries()

    def doctor(self) -> dict[str, object]:
        return {
            "ok": True,
            "name": self.agent.name,
            "tools": self.agent.tools.names(),
            "sessions": [session.id for session in self.list_sessions()],
        }

    def _emit(self, event_type: str, payload: dict[str, object]) -> None:
        event = GatewayEvent(type=event_type, at=self._clock(), payload=payload)
        for listener in self._listeners:
            listener(event)


def create_default_agent(*, clock: Clock | None = None) -> ClawAgent:
    memory = InMemoryStore()
    tools = create_default_tools(clock=clock)
    return ClawAgent(memory=memory, tools=tools)


def create_default_gateway(*, clock: Clock | None = None) -> OpenClawGateway:
    return OpenClawGateway(clock=clock)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
