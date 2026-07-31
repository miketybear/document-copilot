"""add contract to document_type enum

Revision ID: 6a1f4c8d0b57
Revises: 3d7e1c9b5a42
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6a1f4c8d0b57'
down_revision: Union[str, Sequence[str], None] = '3d7e1c9b5a42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE cannot run inside a regular transaction block; autocommit_block()
    # runs it outside the migration's normal transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE document_type ADD VALUE 'contract'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no ALTER TYPE ... DROP VALUE; rebuild the enum without 'contract'. This
    # fails if any source_documents row still has document_type='contract' — reassign or
    # delete those rows before downgrading.
    op.execute("ALTER TYPE document_type RENAME TO document_type_old")
    op.execute("CREATE TYPE document_type AS ENUM ('policy', 'guideline', 'work_instruction')")
    op.execute(
        "ALTER TABLE source_documents ALTER COLUMN document_type "
        "TYPE document_type USING document_type::text::document_type"
    )
    op.execute("DROP TYPE document_type_old")
