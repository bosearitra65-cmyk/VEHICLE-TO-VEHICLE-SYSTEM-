from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firebase_uid: str | None
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    firebase_uid: str | None = Field(default=None, min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(min_length=1, max_length=50)
    is_active: bool = True


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None


class UserAccessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resource_type: str
    resource_id: str
    permission: str
    created_at: datetime
    created_by: int | None


class UserAccessCreate(BaseModel):
    resource_type: str = Field(min_length=1, max_length=50)
    resource_id: str = Field(min_length=1, max_length=100)
    permission: str = Field(min_length=1, max_length=100)
