from datetime import datetime, timedelta, timezone


class VehicleTimestampError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_vehicle_timestamp(
    timestamp: datetime,
    max_future_seconds: int = 30,
    max_past_seconds: int = 300,
) -> None:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)

    if timestamp > now + timedelta(seconds=max_future_seconds):
        raise VehicleTimestampError(
            "Vehicle timestamp is too far in the future"
        )

    if timestamp < now - timedelta(seconds=max_past_seconds):
        raise VehicleTimestampError(
            "Vehicle timestamp is too old"
        )
