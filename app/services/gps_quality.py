from app.schemas.vehicles import VehicleStateIn


class VehicleGPSQualityError(ValueError):
    """Raised when a vehicle GPS quality check fails."""


def validate_gps_quality(payload: VehicleStateIn) -> None:
    if payload.gps_fix is False:
        raise VehicleGPSQualityError("GPS fix is not available")

    if payload.satellites is not None and payload.satellites < 0:
        raise VehicleGPSQualityError("Satellite count cannot be negative")

    if payload.hdop is not None and payload.hdop <= 0:
        raise VehicleGPSQualityError("HDOP must be greater than zero")
