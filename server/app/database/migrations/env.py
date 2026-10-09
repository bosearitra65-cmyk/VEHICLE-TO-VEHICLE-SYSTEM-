from logging.config import fileConfig

from alembic import context

from app.config.settings import settings
from app.database.base import Base
from app.database.connection import engine
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
    context.configure(
        url=engine.url.render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
