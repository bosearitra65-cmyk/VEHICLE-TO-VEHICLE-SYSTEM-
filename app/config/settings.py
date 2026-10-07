from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vehicle Communication Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./vehicle_communication.db"

    api_prefix: str = "/api/v1"

    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    firebase_credentials_file: str = "secrets/firebase-service-account.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
