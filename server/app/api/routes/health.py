from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.config.settings import settings
from app.schemas.common import APIResponse
from app.utils.identifiers import generate_request_id


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("", response_model=APIResponse[dict])
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data={
            "status": "healthy",
            "database": "connected",
            "database_backend": db.get_bind().dialect.name,
            "environment": settings.environment,
        },
    )