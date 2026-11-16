from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.db_connect_timeout},
        hide_parameters=True,
    )


def database_is_ready(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    except SQLAlchemyError:
        # Never expose database credentials or raw connection errors to HTTP clients.
        return False
