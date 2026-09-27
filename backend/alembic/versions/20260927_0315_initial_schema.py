"""initial_schema

Revision ID: fea29d48dcf9
Revises: 
Create Date: 2026-09-27 03:15:43.392103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Safely handle SQLite when SpatiaLite extension is not installed
try:
    from geoalchemy2.admin.dialects import sqlite as _sqlite_admin
    _orig_after_create = _sqlite_admin.after_create
    _orig_before_drop = _sqlite_admin.before_drop

    def _safe_sqlite_after_create(table, bind, **kw):
        try:
            _orig_after_create(table, bind, **kw)
        except Exception:
            pass

    def _safe_sqlite_before_drop(table, bind, **kw):
        try:
            _orig_before_drop(table, bind, **kw)
        except Exception:
            pass

    _sqlite_admin.after_create = _safe_sqlite_after_create
    _sqlite_admin.before_drop = _safe_sqlite_before_drop
except (ImportError, AttributeError):
    pass

# Import all models to ensure metadata is fully populated
from app.db.session import Base
import app.models.rental          # noqa: F401
import app.models.worker          # noqa: F401
import app.models.facility        # noqa: F401
import app.models.routing         # noqa: F401
import app.models.recommendation  # noqa: F401
import app.models.data_source     # noqa: F401


# revision identifiers, used by Alembic.
revision: str = 'fea29d48dcf9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
