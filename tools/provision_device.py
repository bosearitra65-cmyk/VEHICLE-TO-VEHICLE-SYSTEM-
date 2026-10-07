from __future__ import annotations

import argparse

from app.database.session import SessionLocal
from app.services.device_auth import DeviceAuthenticationError, provision_device_credential


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a vehicle device credential")
    parser.add_argument("vehicle_id")
    parser.add_argument("--secret", default=None)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        credential = provision_device_credential(db, args.vehicle_id, args.secret)
    except DeviceAuthenticationError as exc:
        db.rollback()
        raise SystemExit(exc.message) from exc
    finally:
        db.close()
    print(f"vehicle_id={credential.vehicle_id}")
    print(f"device_id={credential.device_id}")
    print(f"secret_version={credential.secret_version}")
    print(f"device_secret={credential.secret}")
    print("Store the device_secret securely. It cannot be recovered from the server.")


if __name__ == "__main__":
    main()
