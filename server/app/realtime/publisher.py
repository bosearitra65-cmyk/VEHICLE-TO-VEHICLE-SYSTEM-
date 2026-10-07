from __future__ import annotations

import asyncio
import itertools
from datetime import datetime, timezone
from typing import Any

from app.realtime.manager import manager


_message_counter = itertools.count(1)
_runtime_loop: asyncio.AbstractEventLoop | None = None


def bind_runtime_loop(
    loop: asyncio.AbstractEventLoop,
) -> None:
    global _runtime_loop
    _runtime_loop = loop


def _message_id() -> str:
    return f"rt-{next(_message_counter)}"


class RealtimePublisher:
    """
    Transport-neutral realtime publisher.

    The authoritative DB/event pipeline calls this publisher after
    state/event creation. WebSocket delivery is only distribution.

    Stage 9 adds explicit message identity so receivers can safely
    deduplicate retransmissions.
    """

    @staticmethod
    def event(
        message_type: str,
        entity_type: str,
        entity_id: str | None,
        payload: dict[str, Any],
        *,
        version: int | None = None,
        vehicle_id: str | None = None,
        convoy_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "message_id": _message_id(),
            "message_type": message_type,
            "server_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "version": version,
            "payload": payload,
            "vehicle_id": vehicle_id,
            "convoy_id": convoy_id,
        }

    async def publish(
        self,
        message_type: str,
        entity_type: str,
        entity_id: str | None,
        payload: dict[str, Any],
        *,
        version: int | None = None,
        vehicle_id: str | None = None,
        convoy_id: str | None = None,
    ) -> int:
        message = self.event(
            message_type,
            entity_type,
            entity_id,
            payload,
            version=version,
            vehicle_id=vehicle_id,
            convoy_id=convoy_id,
        )

        return await manager.publish(
            message,
            entity_type=entity_type,
            entity_id=entity_id,
            vehicle_id=vehicle_id,
            convoy_id=convoy_id,
            version=version,
        )

    def publish_from_sync(
        self,
        message_type: str,
        entity_type: str,
        entity_id: str | None,
        payload: dict[str, Any],
        *,
        version: int | None = None,
        vehicle_id: str | None = None,
        convoy_id: str | None = None,
    ) -> None:
        """
        Safe bridge from existing synchronous services into the
        FastAPI realtime event loop.

        Realtime delivery failure never invalidates authoritative DB state.
        """
        loop = _runtime_loop

        if loop is None or loop.is_closed():
            return

        coroutine = self.publish(
            message_type,
            entity_type,
            entity_id,
            payload,
            version=version,
            vehicle_id=vehicle_id,
            convoy_id=convoy_id,
        )

        try:
            asyncio.run_coroutine_threadsafe(
                coroutine,
                loop,
            )
        except Exception:
            coroutine.close()


publisher = RealtimePublisher()
