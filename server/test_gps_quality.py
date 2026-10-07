import pytest

from app.services.gps_quality import validate_gps_quality


class TestPayload:
    gps_fix = True
    satellites = -1
    hdop = 1.2


def test_negative_satellites_are_rejected():
    with pytest.raises(ValueError, match="Satellite count cannot be negative"):
        validate_gps_quality(TestPayload())
