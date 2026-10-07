from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket


_MAX_SEEN_MESSAGE_IDS = 512

CONNECTION_STATES = {
    "LIVE",
    "FALLBACK",
    "DISCONNECTED",
    "RECONNECTING",
    "SYNC",
}


@dataclass
class RealtimeConnection:
    websocket: WebSocket
    user_id: int
    connection_id: int
    vehicle_ids: set[str] = field(default_factory=set)
    convoy_ids: set[str] = field(default_factory=set)
    last_seen_versions: dict[str, int] = field(default_factory=dict)

    # Stage 9 recovery state.
    connection_state: str = "LIVE"
    last_known_state: dict[str, Any] | None = None

    # Bounded per-connection deduplication window.
    seen_message_ids: set[str] = field(default_factory=set)
    seen_message_order: deque[str] = field(
        default_factory=lambda: deque(
            maxlen=_MAX_SEEN_MESSAGE_IDS
        )
    )


class RealtimeConnectionManager:
    """
    In-process realtime distribution layer.

    REST + database remain authoritative.
    This manager only owns active WebSocket sessions and delivery.

    Stage 9 guarantees:
    - duplicate message suppression
    - stale-version rejection
    - version-gap detection
    - synchronization-required signaling
    - explicit connection recovery state
    - last-known-state caching for fallback
    """

    def __init__(self) -> None:
        self._connections: dict[int, RealtimeConnection] = {}
        self._lock = asyncio.Lock()
        self._next_connection_id = 1

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
    ) -> int:

        async with self._lock:
            connection_id = self._next_connection_id
            self._next_connection_id += 1

            self._connections[connection_id] = RealtimeConnection(
                websocket=websocket,
                user_id=user_id,
                connection_id=connection_id,
                connection_state="LIVE",
            )

        return connection_id

    async def disconnect(
        self,
        connection_id: int,
    ) -> None:
        async with self._lock:
            self._connections.pop(
                connection_id,
                None,
            )

    async def get_connection(
        self,
        connection_id: int,
    ) -> RealtimeConnection | None:
        async with self._lock:
            return self._connections.get(connection_id)

    async def set_connection_state(
        self,
        connection_id: int,
        state: str,
    ) -> bool:
        if state not in CONNECTION_STATES:
            raise ValueError(
                f"Unsupported realtime connection state: {state}"
            )

        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return False

            connection.connection_state = state
            return True

    async def get_connection_state(
        self,
        connection_id: int,
    ) -> str | None:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return None

            return connection.connection_state

    async def set_last_known_state(
        self,
        connection_id: int,
        state: dict[str, Any],
    ) -> bool:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return False

            connection.last_known_state = state
            return True

    async def get_last_known_state(
        self,
        connection_id: int,
    ) -> dict[str, Any] | None:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return None

            return connection.last_known_state

    async def is_live(
        self,
        connection_id: int,
    ) -> bool:
        async with self._lock:
            connection = self._connections.get(
                connection_id
            )

            if connection is None:
                return False

            return connection.connection_state == "LIVE"

    async def subscribe_vehicle(
        self,
        connection_id: int,
        vehicle_id: str,
    ) -> bool:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return False

            connection.vehicle_ids.add(vehicle_id)
            return True

    async def unsubscribe_vehicle(
        self,
        connection_id: int,
        vehicle_id: str,
    ) -> bool:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return False

            connection.vehicle_ids.discard(vehicle_id)
            return True

    async def subscribe_convoy(
        self,
        connection_id: int,
        convoy_id: str,
    ) -> bool:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return False

            connection.convoy_ids.add(convoy_id)
            return True

    async def unsubscribe_convoy(
        self,
        connection_id: int,
        convoy_id: str,
    ) -> bool:
        async with self._lock:
            connection = self._connections.get(connection_id)

            if connection is None:
                return False

            connection.convoy_ids.discard(convoy_id)
            return True

    async def send_to_connection(
        self,
        connection_id: int,
        message: dict[str, Any],
    ) -> bool:
        connection = await self.get_connection(connection_id)

        if connection is None:
            return False

        try:
            await connection.websocket.send_json(message)
            return True
        except Exception:
            await self.disconnect(connection_id)
            return False

    @staticmethod
    def _version_key(
        entity_type: str | None,
        entity_id: str | None,
    ) -> str | None:
        if entity_type is None or entity_id is None:
            return None

        return f"{entity_type}:{entity_id}"

    @staticmethod
    def _remember_message_id(
        connection: RealtimeConnection,
        message_id: str | None,
    ) -> bool:
        if not message_id:
            return False

        if message_id in connection.seen_message_ids:
            return True

        if len(connection.seen_message_order) >= _MAX_SEEN_MESSAGE_IDS:
            oldest = connection.seen_message_order.popleft()
            connection.seen_message_ids.discard(oldest)

        connection.seen_message_order.append(message_id)
        connection.seen_message_ids.add(message_id)

        return False

    @staticmethod
    def _sync_required_message(
        *,
        entity_type: str,
        entity_id: str,
        previous_version: int,
        received_version: int,
    ) -> dict[str, Any]:
        return {
            "message_id": (
                f"sync-required:{entity_type}:"
                f"{entity_id}:{received_version}"
            ),
            "message_type": "SYNC_REQUIRED",
            "server_timestamp": (
                __import__("datetime")
                .datetime.now(
                    __import__("datetime").timezone.utc
                )
                .isoformat()
            ),
            "entity_type": "synchronization",
            "entity_id": entity_id,
            "version": received_version,
            "payload": {
                "reason": "VERSION_GAP",
                "resource_type": entity_type,
                "resource_id": entity_id,
                "last_seen_version": previous_version,
                "received_version": received_version,
                "expected_version": previous_version + 1,
                "authoritative_source": "backend_database",
                "recovery": "REST_API_OR_RESYNC",
            },
            "vehicle_id": None,
            "convoy_id": None,
        }

    async def publish(
        self,
        message: dict[str, Any],
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        vehicle_id: str | None = None,
        convoy_id: str | None = None,
        version: int | None = None,
    ) -> int:
        async with self._lock:
            targets = list(self._connections.items())

        sent = 0
        stale: list[int] = []

        message_id = message.get("message_id")
        version_key = self._version_key(
            entity_type,
            entity_id,
        )

        for connection_id, connection in targets:
            vehicle_match = (
                vehicle_id is not None
                and vehicle_id in connection.vehicle_ids
            )

            convoy_match = (
                convoy_id is not None
                and convoy_id in connection.convoy_ids
            )

            global_match = (
                vehicle_id is None
                and convoy_id is None
            )

            if not (
                vehicle_match
                or convoy_match
                or global_match
            ):
                continue

            # Realtime delivery is operational only for authenticated
            # sessions that have completed synchronization.
            #
            # FALLBACK and SYNC intentionally do not receive ordinary
            # state/event updates until authoritative synchronization
            # restores the connection to LIVE.
            if connection.connection_state != "LIVE":
                continue

            if self._remember_message_id(
                connection,
                message_id,
            ):
                continue

            if (
                version_key is not None
                and version is not None
            ):
                previous = connection.last_seen_versions.get(
                    version_key
                )

                if (
                    previous is not None
                    and version <= previous
                ):
                    continue

                if (
                    previous is not None
                    and version > previous + 1
                ):
                    sync_required = self._sync_required_message(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        previous_version=previous,
                        received_version=version,
                    )

                    try:
                        await connection.websocket.send_json(
                            sync_required
                        )
                        sent += 1
                    except Exception:
                        stale.append(connection_id)

                    continue

            try:
                await connection.websocket.send_json(
                    message
                )
                sent += 1

                if (
                    version_key is not None
                    and version is not None
                ):
                    connection.last_seen_versions[
                        version_key
                    ] = version

            except Exception:
                stale.append(connection_id)

        for connection_id in stale:
            await self.disconnect(connection_id)

        return sent

    async def connection_count(self) -> int:
        async with self._lock:
            return len(self._connections)

    async def subscription_snapshot(
        self,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            return [
                {
                    "connection_id": connection.connection_id,
                    "user_id": connection.user_id,
                    "connection_state": connection.connection_state,
                    "vehicle_ids": sorted(
                        connection.vehicle_ids
                    ),
                    "convoy_ids": sorted(
                        connection.convoy_ids
                    ),
                    "last_seen_versions": dict(
                        connection.last_seen_versions
                    ),
                    "has_last_known_state": (
                        connection.last_known_state is not None
                    ),
                }
                for connection in self._connections.values()
            ]


manager = RealtimeConnectionManager()
