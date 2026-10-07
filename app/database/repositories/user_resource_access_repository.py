from sqlalchemy.orm import Session

from app.models.user_resource_access import UserResourceAccess


class UserResourceAccessRepository:
    def __init__(self, db: Session):
        self.db = db

    def has_access(
        self,
        user_id: int,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        return (
            self.db.query(UserResourceAccess)
            .filter(
                UserResourceAccess.user_id == user_id,
                UserResourceAccess.resource_type == resource_type,
                UserResourceAccess.resource_id == resource_id,
                UserResourceAccess.permission == permission,
            )
            .first()
            is not None
        )

    def get_for_user(
        self,
        user_id: int,
    ) -> list[UserResourceAccess]:
        return (
            self.db.query(UserResourceAccess)
            .filter(UserResourceAccess.user_id == user_id)
            .order_by(UserResourceAccess.id.asc())
            .all()
        )

    def create(
        self,
        user_id: int,
        resource_type: str,
        resource_id: str,
        permission: str,
        created_by: int | None = None,
    ) -> UserResourceAccess:
        access = UserResourceAccess(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            created_by=created_by,
        )
        self.db.add(access)
        self.db.flush()
        return access

    def delete(
        self,
        user_id: int,
        resource_type: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        access = (
            self.db.query(UserResourceAccess)
            .filter(
                UserResourceAccess.user_id == user_id,
                UserResourceAccess.resource_type == resource_type,
                UserResourceAccess.resource_id == resource_id,
                UserResourceAccess.permission == permission,
            )
            .first()
        )

        if access is None:
            return False

        self.db.delete(access)
        self.db.flush()
        return True
