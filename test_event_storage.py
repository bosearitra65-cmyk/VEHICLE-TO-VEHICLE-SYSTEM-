from app.database.session import SessionLocal
from app.models.event import Event


db = SessionLocal()

events = (
    db.query(Event)
    .filter(Event.vehicle_id == "V001")
    .order_by(Event.id.desc())
    .all()
)

for event in events:
    print(
        "ID:", event.id,
        "| Type:", event.event_type,
        "| Severity:", event.severity,
        "| Sequence:", event.sequence_number,
        "| Message:", event.message,
    )

db.close()