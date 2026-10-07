from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.synchronization import build_sync_state
from app.utils.identifiers import generate_request_id


router = APIRouter(
    prefix="/sync",
    tags=["synchronization"],
)


@router.get("", response_model=APIResponse[dict])
def synchronize(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    state = build_sync_state(
        db=db,
        user=current_user,
        connection_state="LIVE",
    )

    state["synchronization_reason"] = "REST_FALLBACK"
    state["recovery_authoritative"] = True

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=state,
    )
