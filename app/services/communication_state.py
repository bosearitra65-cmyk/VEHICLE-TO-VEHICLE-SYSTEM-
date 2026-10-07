from app.config.constants import (
    COMMUNICATION_DISCONNECTED,
    COMMUNICATION_FALLBACK,
    COMMUNICATION_LIVE,
    COMMUNICATION_RECONNECTING,
)


def determine_communication_transition(
    previous_availability: str | None,
    current_availability: str,
) -> str | None:
    if previous_availability == current_availability:
        return None

    if (
        previous_availability == COMMUNICATION_LIVE
        and current_availability == COMMUNICATION_DISCONNECTED
    ):
        return "communication_loss"

    if (
        previous_availability == COMMUNICATION_DISCONNECTED
        and current_availability == COMMUNICATION_LIVE
    ):
        return "communication_recovery"

    if (
        previous_availability == COMMUNICATION_RECONNECTING
        and current_availability == COMMUNICATION_LIVE
    ):
        return "communication_recovery"

    if (
        previous_availability == COMMUNICATION_FALLBACK
        and current_availability == COMMUNICATION_LIVE
    ):
        return "communication_recovery"

    return None