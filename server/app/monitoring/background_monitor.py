import asyncio

from app.database.session import SessionLocal
from app.monitoring.communication_monitor import monitor_vehicle_communications


def run_monitor_cycle(
    freshness_threshold_seconds: int = 10,
) -> list[dict]:
    db = SessionLocal()

    try:
        results = monitor_vehicle_communications(
            db=db,
            freshness_threshold_seconds=freshness_threshold_seconds,
        )
        db.commit()
        return results
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def run_monitor_loop(
    stop_event: asyncio.Event,
    interval_seconds: int = 5,
    freshness_threshold_seconds: int = 10,
) -> None:
    while not stop_event.is_set():
        run_monitor_cycle(
            freshness_threshold_seconds=freshness_threshold_seconds,
        )

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=interval_seconds,
            )
        except asyncio.TimeoutError:
            pass
