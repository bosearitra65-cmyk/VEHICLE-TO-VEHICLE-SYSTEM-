from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.config.settings import settings


database_url = settings.database_url
parsed_url = make_url(database_url)

if parsed_url.drivername in ("postgres", "postgresql"):
    parsed_url = parsed_url.set(drivername="postgresql+psycopg")

connect_args = (
    {"check_same_thread": False}
    if parsed_url.get_backend_name() == "sqlite"
    else {}
)

engine = create_engine(
    parsed_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)
