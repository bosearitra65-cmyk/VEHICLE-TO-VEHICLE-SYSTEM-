from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.vehicle import Vehicle

_SALT_BYTES = 16
_KEY_BYTES = 32
_ITERATIONS = 310_000


class DeviceAuthenticationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ProvisionedDeviceCredential:
    vehicle_id: str
    device_id: str
    secret: str
    secret_version: int


def _derive(secret: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), bytes.fromhex(salt_hex),
        _ITERATIONS, dklen=_KEY_BYTES
    ).hex()


def generate_device_secret() -> str:
    return secrets.token_urlsafe(32)


def provision_device_credential(db: Session, vehicle_id: str, secret: str | None = None) -> ProvisionedDeviceCredential:
    vehicle = VehicleRepository(db).get_by_vehicle_id(vehicle_id)
    if vehicle is None:
        raise DeviceAuthenticationError("Vehicle is not registered")
    if not vehicle.device_id:
        raise DeviceAuthenticationError("Vehicle must have a device_id before provisioning")
    secret = secret or generate_device_secret()
    if len(secret) < 32:
        raise DeviceAuthenticationError("Device secret must contain at least 32 characters")
    salt_hex = secrets.token_hex(_SALT_BYTES)
    vehicle.device_secret_salt = salt_hex
    vehicle.device_secret_hash = _derive(secret, salt_hex)
    vehicle.device_secret_version = (vehicle.device_secret_version or 0) + 1
    vehicle.device_auth_enabled = True
    vehicle.device_last_authenticated_at = None
    db.commit()
    return ProvisionedDeviceCredential(vehicle.vehicle_id, vehicle.device_id, secret, vehicle.device_secret_version)


def authenticate_device(db: Session, device_id: str, secret: str) -> Vehicle:
    vehicle = VehicleRepository(db).get_by_device_id(device_id)
    if vehicle is None or not vehicle.is_active or not vehicle.device_auth_enabled:
        raise DeviceAuthenticationError("Invalid device credentials")
    if not vehicle.device_secret_hash or not vehicle.device_secret_salt:
        raise DeviceAuthenticationError("Device credentials are not provisioned")
    candidate = _derive(secret, vehicle.device_secret_salt)
    if not hmac.compare_digest(candidate, vehicle.device_secret_hash):
        raise DeviceAuthenticationError("Invalid device credentials")
    return vehicle
