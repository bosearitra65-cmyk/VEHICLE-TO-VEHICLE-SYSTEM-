from app.config.constants import (
    COMMUNICATION_DISCONNECTED,
    COMMUNICATION_FALLBACK,
    COMMUNICATION_LIVE,
    COMMUNICATION_RECONNECTING,
)


def determine_availability(
    is_fresh: bool,
    communication_status: str,
) -> str:
    if is_fresh:
        return COMMUNICATION_LIVE

    if communication_status == COMMUNICATION_RECONNECTING:
        return COMMUNICATION_RECONNECTING

    if communication_status == COMMUNICATION_FALLBACK:
        return COMMUNICATION_FALLBACK

    return COMMUNICATION_DISCONNECTED