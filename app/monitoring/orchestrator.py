"""
Stage 7 application-level monitoring orchestration.

The existing monitoring implementation remains authoritative:
    app.monitoring.background_monitor.run_monitor_loop()

This module only owns lifecycle start/stop behavior.
"""

from __future__ import annotations

import asyncio
import logging

from app.monitoring.background_monitor import run_monitor_loop
from app.realtime.publisher import bind_runtime_loop

logger = logging.getLogger(__name__)

_monitor_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


async def start_monitoring(
    interval_seconds: int = 5,
    freshness_threshold_seconds: int = 10,
) -> None:
    """Start the existing monitoring loop exactly once."""
    global _monitor_task, _stop_event

    bind_runtime_loop(asyncio.get_running_loop())

    if _monitor_task is not None and not _monitor_task.done():
        bind_runtime_loop(__import__('asyncio').get_running_loop())
        return


    _stop_event = asyncio.Event()

    _monitor_task = asyncio.create_task(
        run_monitor_loop(
            stop_event=_stop_event,
            interval_seconds=interval_seconds,
            freshness_threshold_seconds=freshness_threshold_seconds,
        )
    )

    logger.info("Vehicle monitoring loop started")


async def stop_monitoring() -> None:
    """Stop the existing monitoring loop cleanly."""
    global _monitor_task, _stop_event

    if _stop_event is not None:
        _stop_event.set()

    if _monitor_task is not None:
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        finally:
            _monitor_task = None

    _stop_event = None

    logger.info("Vehicle monitoring loop stopped")
