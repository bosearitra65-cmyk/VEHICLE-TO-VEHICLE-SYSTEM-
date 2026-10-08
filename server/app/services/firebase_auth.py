from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials

from app.config.settings import settings


class FirebaseAuthenticationError(Exception):
    """Raised when Firebase authentication cannot be initialized or verified."""


def _initialize_firebase() -> None:
    if firebase_admin._apps:
        return

    try:
        if settings.firebase_project_id and settings.firebase_client_email and settings.firebase_private_key:
            credential = credentials.Certificate({
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "private_key": settings.firebase_private_key.replace("\\n", "\n"),
                "client_email": settings.firebase_client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            })
        else:
            credentials_path = Path(settings.firebase_credentials_file)

            if not credentials_path.is_absolute():
                credentials_path = Path(__file__).resolve().parents[3] / credentials_path

            if not credentials_path.is_file():
                raise FirebaseAuthenticationError(
                    "Firebase service-account credential file was not found"
                )

            credential = credentials.Certificate(str(credentials_path))

        firebase_admin.initialize_app(credential)

    except FirebaseAuthenticationError:
        raise
    except Exception as exc:
        raise FirebaseAuthenticationError(
            "Firebase Admin SDK initialization failed"
        ) from exc

def verify_firebase_token(id_token: str) -> dict[str, Any]:
    if not id_token or not id_token.strip():
        raise FirebaseAuthenticationError("Firebase ID token is required")

    try:
        _initialize_firebase()
        return auth.verify_id_token(id_token)
    except FirebaseAuthenticationError:
        raise
    except Exception as exc:
        raise FirebaseAuthenticationError(
            "Firebase ID token verification failed"
        ) from exc
