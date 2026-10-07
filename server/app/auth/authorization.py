from collections.abc import Collection

from app.auth.permissions import Permission
from app.auth.roles import UserRole
from app.models.user import User


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMINISTRATOR: frozenset(
        {
            Permission.VEHICLE_VIEW,
            Permission.VEHICLE_MANAGE,
            Permission.CONVOY_VIEW,
            Permission.CONVOY_MANAGE,
            Permission.CONVOY_LEADER_ASSIGN,
            Permission.JOURNEY_VIEW,
            Permission.JOURNEY_MANAGE,
            Permission.ROUTE_VIEW,
            Permission.ROUTE_MANAGE,
            Permission.ALERTS_VIEW,
            Permission.EVENTS_VIEW,
            Permission.HISTORY_VIEW,
            Permission.RESEARCH_VIEW,
            Permission.RESEARCH_CREATE,
            Permission.RESEARCH_CONFIGURE,
            Permission.RESEARCH_RUN,
            Permission.RESEARCH_FAULT_CONTROL,
            Permission.RESEARCH_ANALYZE,
            Permission.RESEARCH_EVIDENCE_MANAGE,
            Permission.USER_MANAGE,
            Permission.ACCESS_MANAGE,
            Permission.SYSTEM_CONFIGURE,
        }
    ),
    UserRole.VEHICLE_USER: frozenset(
        {
            Permission.VEHICLE_VIEW,
            Permission.CONVOY_VIEW,
            Permission.JOURNEY_VIEW,
            Permission.ROUTE_VIEW,
            Permission.ALERTS_VIEW,
            Permission.EVENTS_VIEW,
            Permission.HISTORY_VIEW,
        }
    ),
    UserRole.RESEARCHER: frozenset(
        {
            Permission.VEHICLE_VIEW,
            Permission.CONVOY_VIEW,
            Permission.JOURNEY_VIEW,
            Permission.ROUTE_VIEW,
            Permission.ALERTS_VIEW,
            Permission.EVENTS_VIEW,
            Permission.HISTORY_VIEW,
            Permission.RESEARCH_VIEW,
            Permission.RESEARCH_CREATE,
            Permission.RESEARCH_CONFIGURE,
            Permission.RESEARCH_RUN,
            Permission.RESEARCH_FAULT_CONTROL,
            Permission.RESEARCH_ANALYZE,
            Permission.RESEARCH_EVIDENCE_MANAGE,
        }
    ),
}


def get_role_permissions(role: str) -> frozenset[Permission]:
    try:
        user_role = UserRole(role)
    except ValueError:
        return frozenset()

    return ROLE_PERMISSIONS.get(user_role, frozenset())


def get_user_permissions(
    user: User,
    additional_permissions: Collection[str] | None = None,
) -> frozenset[str]:
    permissions = {
        permission.value
        for permission in get_role_permissions(user.role)
    }

    if additional_permissions:
        permissions.update(additional_permissions)

    return frozenset(permissions)


def has_permission(
    user: User,
    permission: Permission | str,
    additional_permissions: Collection[str] | None = None,
) -> bool:
    permission_value = (
        permission.value
        if isinstance(permission, Permission)
        else permission
    )

    return permission_value in get_user_permissions(
        user=user,
        additional_permissions=additional_permissions,
    )


def has_resource_access(
    user: User,
    permission: Permission | str,
    resource_type: str,
    resource_id: str,
    resource_access_checker,
) -> bool:
    permission_value = (
        permission.value
        if isinstance(permission, Permission)
        else permission
    )

    if not has_permission(user, permission_value):
        return False

    if user.role == UserRole.ADMINISTRATOR.value:
        return True

    return resource_access_checker(
        user.id,
        resource_type,
        resource_id,
        permission_value,
    )
