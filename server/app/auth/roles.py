from enum import StrEnum

from app.config.constants import (
    ROLE_ADMINISTRATOR,
    ROLE_RESEARCHER,
    ROLE_VEHICLE_USER,
)


class UserRole(StrEnum):
    ADMINISTRATOR = ROLE_ADMINISTRATOR
    VEHICLE_USER = ROLE_VEHICLE_USER
    RESEARCHER = ROLE_RESEARCHER


def is_valid_role(role: str) -> bool:
    return role in {item.value for item in UserRole}
