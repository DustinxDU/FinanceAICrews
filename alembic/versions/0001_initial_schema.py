"""Initial schema for FinanceAICrews Community Edition.

This is a consolidated migration that creates the complete database schema.
All 0 incremental migrations from development have been squashed into this single file.

For fresh installations:
    1. Configure your DATABASE_URL in .env
    2. Run: alembic upgrade head
    3. Run: python scripts/seeding/seed_all.py

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    # Downgrade is not supported for consolidated migration
    # To reset, drop all tables and run upgrade again
    raise NotImplementedError(
        "Downgrade is not supported for consolidated migration. "
        "To reset the database, drop all tables and run 'alembic upgrade head' again."
    )
