from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_permission
from app.auth.permissions import Permission
from app.database.repositories.alert_repository import AlertRepository
from app.database.repositories.vehicle_repository import VehicleRepository
from app.models.alert import Alert
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.operational import AlertOut
from app.utils.identifiers import generate_request_id


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=APIResponse[list[AlertOut]])
def list_alerts(
    vehicle_id: str | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ALERTS_VIEW)),
):
    repository = AlertRepository(db)

    if vehicle_id is not None:
        if VehicleRepository(db).get_by_vehicle_id(vehicle_id) is None:
            raise HTTPException(status_code=404, detail="Vehicle not found")

        if active_only:
            alerts = repository.list_active_by_vehicle(vehicle_id)
        else:
            alerts = repository.list_by_vehicle(vehicle_id)
    else:
        if active_only:
            raise HTTPException(
                status_code=400,
                detail="active_only requires vehicle_id",
            )

        alerts = db.query(Alert).order_by(Alert.id.asc()).all()

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=[AlertOut.model_validate(item) for item in alerts],
    )


@router.get(
    "/{alert_id}",
    response_model=APIResponse[AlertOut],
)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ALERTS_VIEW)),
):
    alert = AlertRepository(db).get_by_id(alert_id)

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=AlertOut.model_validate(alert),
    )


@router.post(
    "/{alert_id}/resolve",
    response_model=APIResponse[AlertOut],
)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ALERTS_VIEW)),
):
    repository = AlertRepository(db)
    alert = repository.get_by_id(alert_id)

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    if not alert.is_active:
        raise HTTPException(status_code=409, detail="Alert is already resolved")

    repository.resolve(alert)
    db.commit()
    db.refresh(alert)

    return APIResponse(
        request_id=generate_request_id(),
        server_timestamp=datetime.now(timezone.utc),
        data=AlertOut.model_validate(alert),
    )
