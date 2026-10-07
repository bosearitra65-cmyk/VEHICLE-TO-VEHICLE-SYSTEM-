from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        user_id: int,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_all(self) -> list[User]:
        return (
            self.db.query(User)
            .order_by(User.id.asc())
            .all()
        )

    def get_by_firebase_uid(
        self,
        firebase_uid: str,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.firebase_uid == firebase_uid)
            .first()
        )

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )

    def create(
        self,
        firebase_uid: str | None,
        email: str,
        role: str,
        is_active: bool = True,
    ) -> User:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            role=role,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update(
        self,
        user: User,
        **fields,
    ) -> User:
        for field, value in fields.items():
            setattr(user, field, value)

        self.db.flush()
        return user
