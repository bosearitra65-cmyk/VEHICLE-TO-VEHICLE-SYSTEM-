from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.convoy_intelligence.service import (
    calculate_convoy_intelligence,
    calculate_vehicle_pair_distance,
)


router = APIRouter(
    prefix="/convoys",
    tags=["Convoy Intelligence"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/{convoy_id}/intelligence")
def get_convoy_intelligence(
    convoy_id: str,
    separation_warning_m: float = 100.0,
    db: Session = Depends(get_db),
):
    try:
        result = calculate_convoy_intelligence(
            db=db,
            convoy_id=convoy_id,
            separation_warning_m=separation_warning_m,
        )

        return {
            "success": True,
            "data": result.to_dict(),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{convoy_id}/vehicles/{vehicle_id}/relationships"
)
def get_vehicle_relationships(
    convoy_id: str,
    vehicle_id: str,
    separation_warning_m: float = 100.0,
    db: Session = Depends(get_db),
):
    try:
        result = calculate_convoy_intelligence(
            db=db,
            convoy_id=convoy_id,
            separation_warning_m=separation_warning_m,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    vehicle = next(
        (
            item
            for item in result.vehicles
            if item["vehicle_id"] == vehicle_id
        ),
        None,
    )

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Vehicle {vehicle_id} is not an "
                f"active member of convoy {convoy_id}"
            ),
        )

    return {
        "success": True,
        "data": {
            "convoy_id": convoy_id,
            "vehicle": vehicle,
        },
    }


@router.get("/distance/{vehicle_a_id}/{vehicle_b_id}")
def get_vehicle_pair_distance(
    vehicle_a_id: str,
    vehicle_b_id: str,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": calculate_vehicle_pair_distance(
            db,
            vehicle_a_id,
            vehicle_b_id,
        ),
    }
