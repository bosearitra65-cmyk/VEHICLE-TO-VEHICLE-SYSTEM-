from app.config.constants import (
    EVENT_GPS_QUALITY,
    EVENT_COMMUNICATION_LOSS,
    EVENT_ROUTE_DEVIATION,
)
from app.models.event import Event


def should_create_alert(event: Event) -> bool:
    if event.event_type == EVENT_ROUTE_DEVIATION:
        return True
    if event.event_type == EVENT_GPS_QUALITY:
        return event.severity == "warning"

    if event.event_type == EVENT_COMMUNICATION_LOSS:
        return event.severity == "critical"

    return False