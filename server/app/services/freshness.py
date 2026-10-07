from datetime import datetime, timezone


def calculate_age_seconds(timestamp: datetime) -> float:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)

    return max(
        0.0,
        (now - timestamp).total_seconds(),
    )


def is_fresh(
    timestamp: datetime,
    freshness_threshold_seconds: int = 10,
) -> bool:
    age_seconds = calculate_age_seconds(timestamp)

    return age_seconds <= freshness_threshold_seconds