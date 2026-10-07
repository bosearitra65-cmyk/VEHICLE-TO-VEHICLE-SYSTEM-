from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.vehicle import Vehicle
from app.services.location.map_service import (
    build_map_vehicle,
    list_map_vehicles,
)


router = APIRouter(
    prefix="/map",
    tags=["Map"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/vehicles")
def get_map_vehicles(
    db: Session = Depends(get_db),
):
    vehicles = list_map_vehicles(db)

    return {
        "data": vehicles,
        "count": len(vehicles),
    }


@router.get("/vehicles/{vehicle_id}")
def get_map_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
):
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == vehicle_id)
        .first()
    )

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found",
        )

    result = build_map_vehicle(db, vehicle_id)

    return {
        "data": result.to_dict(),
    }
