from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.database.base import Base
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_state import VehicleState
from app.models.vehicle_session import VehicleSession
from app.models.event import Event
from app.models.alert import Alert
from app.models.vehicle_history import VehicleHistory
from app.models.convoy import Convoy
from app.models.convoy_member import ConvoyMember
from app.models.journey import Journey
from app.models.route import Route
from app.models.user_resource_access import UserResourceAccess
from app.models.research_records import ResearchExperimentRecord, ResearchRunRecord

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
