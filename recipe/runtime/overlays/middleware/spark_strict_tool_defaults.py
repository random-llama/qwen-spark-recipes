"""ASGI middleware that supplies omitted strict defaults for one Qwen endpoint."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any


ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]


class StrictToolDefaults:
    """Set ``function.strict`` only when it is omitted for the selected request shape."""

    MAX_BODY_BYTES = 8 * 1024 * 1024

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[[], Awaitable[dict[str, Any]]], send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        if not self._is_candidate_scope(scope):
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.MAX_BODY_BYTES:
            await self.app(scope, receive, send)
            return

        messages, body, complete = await self._read_bounded(receive)
        if not complete or body is None:
            await self.app(scope, self._replay(messages, receive), send)
            return

        try:
            request = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            await self.app(scope, self._replay(messages, receive), send)
            return

        changed = self._set_missing_strict_defaults(request)
        if changed is None:
            await self.app(scope, self._replay(messages, receive), send)
            return

        encoded = json.dumps(changed, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        updated_scope = dict(scope)
        updated_scope["headers"] = self._headers_with_content_length(scope.get("headers", []), len(encoded))
        await self.app(updated_scope, self._replay([{"type": "http.request", "body": encoded, "more_body": False}], receive), send)

    @classmethod
    def _is_candidate_scope(cls, scope: dict[str, Any]) -> bool:
        if scope.get("type") != "http" or scope.get("method") != "POST" or scope.get("path") != "/v1/chat/completions":
            return False
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-type":
                return value.split(b";", 1)[0].strip().lower() == b"application/json"
        return False

    @classmethod
    def _content_length(cls, scope: dict[str, Any]) -> int | None:
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None

    async def _read_bounded(self, receive: Callable[[], Awaitable[dict[str, Any]]]) -> tuple[list[dict[str, Any]], bytes | None, bool]:
        messages: list[dict[str, Any]] = []
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            messages.append(message)
            if message.get("type") == "http.disconnect":
                return messages, None, False
            if message.get("type") != "http.request":
                return messages, None, False
            chunk = message.get("body", b"")
            if not isinstance(chunk, bytes):
                return messages, None, False
            size += len(chunk)
            if size > self.MAX_BODY_BYTES:
                return messages, None, False
            chunks.append(chunk)
            if not message.get("more_body", False):
                return messages, b"".join(chunks), True

    @staticmethod
    def _replay(messages: list[dict[str, Any]], receive: Callable[[], Awaitable[dict[str, Any]]]) -> Callable[[], Awaitable[dict[str, Any]]]:
        index = 0

        async def replay() -> dict[str, Any]:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return await receive()

        return replay

    @staticmethod
    def _headers_with_content_length(headers: list[tuple[bytes, bytes]], body_length: int) -> list[tuple[bytes, bytes]]:
        result = [(key, value) for key, value in headers if key.lower() != b"content-length"]
        result.append((b"content-length", str(body_length).encode("ascii")))
        return result

    @staticmethod
    def _set_missing_strict_defaults(request: Any) -> dict[str, Any] | None:
        if not isinstance(request, dict):
            return None
        if request.get("model") != "qwen38-flash-next":
            return None
        tools = request.get("tools")
        if not isinstance(tools, list) or not tools:
            return None
        if "tool_choice" in request and request["tool_choice"] != "auto":
            return None

        updated_tools: list[Any] | None = None
        for index, tool in enumerate(tools):
            if not isinstance(tool, dict) or tool.get("type") != "function":
                continue
            function = tool.get("function")
            if not isinstance(function, dict) or function.get("strict") is not None:
                continue
            if updated_tools is None:
                updated_tools = list(tools)
            updated_function = dict(function)
            updated_function["strict"] = True
            updated_tool = dict(tool)
            updated_tool["function"] = updated_function
            updated_tools[index] = updated_tool
        if updated_tools is None:
            return None
        updated_request = dict(request)
        updated_request["tools"] = updated_tools
        return updated_request
