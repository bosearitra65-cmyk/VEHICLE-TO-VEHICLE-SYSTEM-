from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.services.synchronization import build_sync_state
from app.auth.authorization import has_permission, has_resource_access
from app.auth.permissions import Permission
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.user_resource_access_repository import (
    UserResourceAccessRepository,
)
from app.database.session import SessionLocal
from app.realtime.manager import manager
from app.services.firebase_auth import (
    FirebaseAuthenticationError,
    verify_firebase_token,
)


router = APIRouter(
    prefix="/realtime",
    tags=["realtime"],
)


def _permission_candidate(*names: str) -> str | Permission | None:
    for name in names:
        if hasattr(Permission, name):
            return getattr(Permission, name)
    return None


def _authenticate_token(
    token: str,
    db: Session,
):
    try:
        decoded = verify_firebase_token(token)
    except FirebaseAuthenticationError as exc:
        raise ValueError(str(exc)) from exc

    firebase_uid = decoded.get("uid")

    if not firebase_uid:
        raise ValueError(
            "Firebase token does not contain a user ID"
        )

    user = UserRepository(db).get_by_firebase_uid(
        firebase_uid
    )

    if user is None:
        raise ValueError(
            "Authenticated user is not registered"
        )

    if not user.is_active:
        raise ValueError(
            "User account is inactive"
        )

    return user


def _authorized_for_resource(
    db: Session,
    user,
    resource_type: str,
    resource_id: str,
) -> bool:
    repository = UserResourceAccessRepository(db)

    permission = _permission_candidate(
        f"{resource_type.upper()}_READ",
        f"{resource_type.upper()}_VIEW",
        f"VIEW_{resource_type.upper()}",
        f"READ_{resource_type.upper()}",
    )

    if permission is not None:
        try:
            return has_resource_access(
                user=user,
                permission=permission,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_access_checker=repository.has_access,
            )
        except Exception:
            pass

    generic = _permission_candidate(
        "VEHICLE_READ",
        "VEHICLE_VIEW",
        "VIEW_VEHICLES",
        "READ_VEHICLES",
    )

    if resource_type == "vehicle" and generic is not None:
        return has_permission(user, generic)

    generic = _permission_candidate(
        "CONVOY_READ",
        "CONVOY_VIEW",
        "VIEW_CONVOYS",
        "READ_CONVOYS",
    )

    if resource_type == "convoy" and generic is not None:
        return has_permission(user, generic)

    return str(
        getattr(user, "role", "")
    ).lower() in {
        "administrator",
        "admin",
    }


def _state_message(
    *,
    connection_id: int,
    state: str,
    reason: str,
) -> dict:
    return {
        "message_id": (
            f"connection-state:{connection_id}:"
            f"{state}:{reason}"
        ),
        "message_type": "CONNECTION_STATE_CHANGED",
        "server_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "entity_type": "connection",
        "entity_id": str(connection_id),
        "version": 1,
        "payload": {
            "connection_id": connection_id,
            "state": state,
            "reason": reason,
            "authoritative_source": "backend_database",
        },
        "vehicle_id": None,
        "convoy_id": None,
    }


def _error_message(
    *,
    connection_id: int,
    reason: str,
    recoverable: bool = True,
) -> dict:
    return {
        "message_id": (
            f"realtime-error:{connection_id}:{reason}"
        ),
        "message_type": "REALTIME_ERROR",
        "server_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "entity_type": "connection",
        "entity_id": str(connection_id),
        "version": 1,
        "payload": {
            "reason": reason,
            "recoverable": recoverable,
            "fallback": "REST_API",
        },
        "vehicle_id": None,
        "convoy_id": None,
    }


async def _require_live_session(
    websocket: WebSocket,
    connection_id: int,
) -> bool:
    if await manager.is_live(connection_id):
        return True

    await websocket.send_json(
        _error_message(
            connection_id=connection_id,
            reason="CONNECTION_NOT_LIVE",
            recoverable=True,
        )
    )
    return False


async def _send_state_change(
    websocket: WebSocket,
    connection_id: int,
    state: str,
    reason: str,
) -> None:
    await manager.set_connection_state(
        connection_id,
        state,
    )

    await websocket.send_json(
        _state_message(
            connection_id=connection_id,
            state=state,
            reason=reason,
        )
    )


async def _perform_authoritative_sync(
    websocket: WebSocket,
    db: Session,
    user,
    connection_id: int,
    reason: str,
) -> bool:
    """
    Perform one authoritative synchronization transaction.

    The database-backed synchronization service is the only source
    of recovered state. The cached last-known state is updated only
    after the authoritative snapshot has been successfully produced.
    """
    await _send_state_change(
        websocket,
        connection_id,
        "SYNC",
        reason,
    )

    try:
        sync_state = build_sync_state(
            db=db,
            user=user,
            connection_state="SYNC",
        )

        sync_state["synchronization_reason"] = reason
        sync_state["recovery_authoritative"] = True

        await manager.set_last_known_state(
            connection_id,
            sync_state,
        )

        await websocket.send_json({
            "message_id": (
                f"sync-completed-{connection_id}-"
                f"{reason.lower()}"
            ),
            "message_type": "SYNC_COMPLETED",
            "server_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "entity_type": "synchronization",
            "entity_id": str(connection_id),
            "version": 1,
            "payload": {
                "reason": reason,
                "state": sync_state,
                "connection_state": "SYNC",
                "authoritative_source": "backend_database",
            },
            "vehicle_id": None,
            "convoy_id": None,
        })

        await _send_state_change(
            websocket,
            connection_id,
            "LIVE",
            f"{reason}_COMPLETED",
        )

        return True

    except Exception as exc:
        await websocket.send_json(
            _error_message(
                connection_id=connection_id,
                reason=(
                    f"SYNCHRONIZATION_FAILED:"
                    f"{type(exc).__name__}"
                ),
                recoverable=True,
            )
        )

        await _send_state_change(
            websocket,
            connection_id,
            "FALLBACK",
            "SYNCHRONIZATION_FAILED",
        )

        return False


@router.websocket("/ws")
async def realtime_websocket(
    websocket: WebSocket,
):
    """
    Authenticated realtime endpoint.

    Authentication occurs through the first WebSocket message:

        {"action": "authenticate", "token": "<Firebase ID token>"}

    REST + database remain authoritative.
    """

    await websocket.accept()

    db = SessionLocal()
    connection_id: int | None = None

    try:
        try:
            auth_message = await websocket.receive_json()
        except Exception:
            await websocket.send_json({
                "message_type": "AUTHENTICATION_REQUIRED",
                "payload": {
                    "reason": (
                        "Initial authentication message is required"
                    )
                },
            })
            return

        if auth_message.get("action") != "authenticate":
            await websocket.send_json({
                "message_type": "AUTHENTICATION_REQUIRED",
                "payload": {
                    "reason": (
                        "First message must authenticate "
                        "the connection"
                    )
                },
            })
            return

        token = str(
            auth_message.get("token") or ""
        ).strip()

        if not token:
            await websocket.send_json({
                "message_type": "AUTHENTICATION_FAILED",
                "payload": {
                    "reason": (
                        "Firebase ID token is required"
                    )
                },
            })
            return

        try:
            user = _authenticate_token(
                token,
                db,
            )
        except ValueError as exc:
            await websocket.send_json({
                "message_type": "AUTHENTICATION_FAILED",
                "payload": {
                    "reason": str(exc)
                },
            })
            return

        connection_id = await manager.connect(
            websocket,
            user_id=user.id,
        )

        await websocket.send_json({
            "message_id": "connection-ready",
            "message_type": "CONNECTION_READY",
            "server_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "entity_type": "connection",
            "entity_id": str(connection_id),
            "version": 1,
            "payload": {
                "connection_id": connection_id,
                "user_id": user.id,
                "realtime_protocol_version": "1.0",
                "authoritative_source": "backend_database",
                "fallback": "REST_API",
                "connection_state": "RECONNECTING",
            },
            "vehicle_id": None,
            "convoy_id": None,
        })

        # Explicit recovery lifecycle begins after authentication.
        await _send_state_change(
            websocket,
            connection_id,
            "RECONNECTING",
            "AUTHENTICATED_CONNECTION",
        )

        initial_sync_ok = await _perform_authoritative_sync(
            websocket=websocket,
            db=db,
            user=user,
            connection_id=connection_id,
            reason="INITIAL_CONNECTION",
        )

        if not initial_sync_ok:
            return

        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                await manager.set_connection_state(
                    connection_id,
                    "DISCONNECTED",
                )
                raise
            except Exception as exc:
                await websocket.send_json(
                    _error_message(
                        connection_id=connection_id,
                        reason=f"RECEIVE_FAILURE:{type(exc).__name__}",
                    )
                )

                await _send_state_change(
                    websocket,
                    connection_id,
                    "FALLBACK",
                    "REALTIME_RECEIVE_FAILURE",
                )
                continue

            action = message.get("action")

            if action == "ping":
                await websocket.send_json({
                    "message_type": "PONG",
                    "payload": {
                        "connection_state": (
                            await manager.get_connection_state(
                                connection_id
                            )
                        )
                    },
                })
                continue

            if action == "subscribe_vehicle":
                if not await _require_live_session(
                    websocket,
                    connection_id,
                ):
                    continue

                vehicle_id = str(
                    message.get("vehicle_id") or ""
                ).strip()

                if not vehicle_id:
                    await websocket.send_json({
                        "message_type": "ERROR",
                        "payload": {
                            "reason": "vehicle_id is required"
                        },
                    })
                    continue

                if not _authorized_for_resource(
                    db,
                    user,
                    "vehicle",
                    vehicle_id,
                ):
                    await websocket.send_json({
                        "message_type": "AUTHORIZATION_DENIED",
                        "payload": {
                            "resource_type": "vehicle",
                            "resource_id": vehicle_id,
                        },
                    })
                    continue

                await manager.subscribe_vehicle(
                    connection_id,
                    vehicle_id,
                )

                await websocket.send_json({
                    "message_type": "SUBSCRIPTION_UPDATED",
                    "payload": {
                        "resource_type": "vehicle",
                        "resource_id": vehicle_id,
                        "subscribed": True,
                    },
                })
                continue

            if action == "unsubscribe_vehicle":
                if not await _require_live_session(
                    websocket,
                    connection_id,
                ):
                    continue

                vehicle_id = str(
                    message.get("vehicle_id") or ""
                ).strip()

                if vehicle_id:
                    if not _authorized_for_resource(
                        db,
                        user,
                        "vehicle",
                        vehicle_id,
                    ):
                        await websocket.send_json({
                            "message_type": "AUTHORIZATION_DENIED",
                            "payload": {
                                "resource_type": "vehicle",
                                "resource_id": vehicle_id,
                            },
                        })
                        continue

                    await manager.unsubscribe_vehicle(
                        connection_id,
                        vehicle_id,
                    )

                await websocket.send_json({
                    "message_type": "SUBSCRIPTION_UPDATED",
                    "payload": {
                        "resource_type": "vehicle",
                        "resource_id": vehicle_id,
                        "subscribed": False,
                    },
                })
                continue

            if action == "subscribe_convoy":
                if not await _require_live_session(
                    websocket,
                    connection_id,
                ):
                    continue

                convoy_id = str(
                    message.get("convoy_id") or ""
                ).strip()

                if not convoy_id:
                    await websocket.send_json({
                        "message_type": "ERROR",
                        "payload": {
                            "reason": "convoy_id is required"
                        },
                    })
                    continue

                if not _authorized_for_resource(
                    db,
                    user,
                    "convoy",
                    convoy_id,
                ):
                    await websocket.send_json({
                        "message_type": "AUTHORIZATION_DENIED",
                        "payload": {
                            "resource_type": "convoy",
                            "resource_id": convoy_id,
                        },
                    })
                    continue

                await manager.subscribe_convoy(
                    connection_id,
                    convoy_id,
                )

                await websocket.send_json({
                    "message_type": "SUBSCRIPTION_UPDATED",
                    "payload": {
                        "resource_type": "convoy",
                        "resource_id": convoy_id,
                        "subscribed": True,
                    },
                })
                continue

            if action == "unsubscribe_convoy":
                if not await _require_live_session(
                    websocket,
                    connection_id,
                ):
                    continue

                convoy_id = str(
                    message.get("convoy_id") or ""
                ).strip()

                if convoy_id:
                    if not _authorized_for_resource(
                        db,
                        user,
                        "convoy",
                        convoy_id,
                    ):
                        await websocket.send_json({
                            "message_type": "AUTHORIZATION_DENIED",
                            "payload": {
                                "resource_type": "convoy",
                                "resource_id": convoy_id,
                            },
                        })
                        continue

                    await manager.unsubscribe_convoy(
                        connection_id,
                        convoy_id,
                    )

                await websocket.send_json({
                    "message_type": "SUBSCRIPTION_UPDATED",
                    "payload": {
                        "resource_type": "convoy",
                        "resource_id": convoy_id,
                        "subscribed": False,
                    },
                })
                continue

            if action == "resync":
                await _send_state_change(
                    websocket,
                    connection_id,
                    "RECONNECTING",
                    "RESYNC_REQUESTED",
                )

                await _perform_authoritative_sync(
                    websocket=websocket,
                    db=db,
                    user=user,
                    connection_id=connection_id,
                    reason="RECONNECT",
                )
                continue

            await websocket.send_json({
                "message_type": "ERROR",
                "payload": {
                    "reason": "Unknown realtime action"
                },
            })

    except WebSocketDisconnect:
        if connection_id is not None:
            try:
                await manager.set_connection_state(
                    connection_id,
                    "DISCONNECTED",
                )
            except Exception:
                pass
    finally:
        if connection_id is not None:
            await manager.disconnect(connection_id)

        db.close()
