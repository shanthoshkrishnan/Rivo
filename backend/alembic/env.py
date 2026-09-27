"""
RIVO Backend — Alembic Migration Environment
=============================================
Configures Alembic to:
  1. Load the database URL from the application settings (env vars / .env)
  2. Import all ORM models so autogenerate can detect schema changes
  3. Support both offline (SQL script) and online (live DB) migration modes

To generate a new migration:
    alembic revision --autogenerate -m "add_some_table"

To apply all pending migrations:
    alembic upgrade head

To roll back one migration:
    alembic downgrade -1
"""
from logging.config import fileConfig
import os
import sys

# Ensure the backend app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from sqlalchemy import engine_from_config, pool

# Load RIVO settings
from app.core.config import get_settings

# Import all models so Alembic autogenerate picks them up
from app.db.session import Base
import app.models.rental          # noqa: F401
import app.models.worker          # noqa: F401
import app.models.facility        # noqa: F401
import app.models.routing         # noqa: F401
import app.models.recommendation  # noqa: F401
import app.models.data_source     # noqa: F401

settings = get_settings()

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override URL from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL script without connecting to the DB.
    Useful for reviewing or applying migrations manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Connects to PostgreSQL if available, otherwise falls back to local SQLite.
    """
    connection = None
    try:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        connection = connectable.connect()
    except Exception:
        # Fall back to local SQLite database in dev
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "data", "rivo.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        from sqlalchemy import create_engine
        connectable = create_engine(f"sqlite:///{db_path}", poolclass=pool.NullPool)
        connection = connectable.connect()

    with connection:
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
