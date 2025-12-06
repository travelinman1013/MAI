"""Enable pgvector extension

Revision ID: d1f998463c8e
Revises: 8c6931db4b0d
Create Date: 2025-12-05 17:07:28.298966

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1f998463c8e'
down_revision = '8c6931db4b0d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
