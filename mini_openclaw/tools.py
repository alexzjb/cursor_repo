from __future__ import annotations

import datetime as dt
import ast
import operator
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .types import InboundMessage, ToolResult


ToolHandler = Callable[[dict[str, Any], "ToolContext"], Any]


@dataclass(frozen=True)
class ToolContext:
    message: InboundMessage
    memory: Any


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def describe(self) -> list[dict[str, str]]:
        return [{"name": tool.name, "description": tool.description} for tool in self._tools.values()]

    def run(self, name: str, args: dict[str, Any], *, message: InboundMessage, memory: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name=name, ok=False, error=f"unknown tool: {name}")

        try:
            context = ToolContext(message=message, memory=memory)
            output = tool.handler(args, context)
            return ToolResult(name=name, ok=True, output=output)
        except Exception as exc:  # pragma: no cover - defensive tool boundary
            return ToolResult(name=name, ok=False, error=str(exc))


def create_default_tools(clock: Callable[[], dt.datetime | str] | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    now = clock or (lambda: dt.datetime.now(dt.UTC))

    def echo(args: dict[str, Any], _context: ToolContext) -> str:
        return str(args.get("text", ""))

    def time(_args: dict[str, Any], _context: ToolContext) -> str:
        current = now()
        return current if isinstance(current, str) else current.isoformat()

    def remember(args: dict[str, Any], context: ToolContext) -> str:
        note = str(args.get("note", "")).strip()
        if not note:
            raise ValueError('remember requires {"note": "..."}')
        context.memory.remember(context.message.session_id, note)
        return f"Remembered: {note}"

    def calc(args: dict[str, Any], _context: ToolContext) -> str:
        expr = str(args.get("expr", "")).strip()
        if not expr:
            raise ValueError('calc requires {"expr": "..."}')
        return str(_safe_eval(expr))

    registry.register(Tool("echo", "Return the provided text.", echo))
    registry.register(Tool("time", "Return the current ISO timestamp.", time))
    registry.register(Tool("calc", "Evaluate a basic arithmetic expression.", calc))
    registry.register(Tool("remember", "Store a note in the local session.", remember))
    return registry


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expression: str) -> int | float:
    node = ast.parse(expression, mode="eval")
    return _eval_node(node.body)


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError("calc only supports numeric arithmetic")
