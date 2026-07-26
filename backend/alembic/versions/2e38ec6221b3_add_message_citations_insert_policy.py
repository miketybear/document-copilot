"""add message_citations insert policy

Revision ID: 2e38ec6221b3
Revises: 72b7224321fb
Create Date: 2026-07-25 18:03:52.135923

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2e38ec6221b3'
down_revision: Union[str, Sequence[str], None] = '72b7224321fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The initial migration only added a SELECT policy for message_citations. The chat
    # orchestrator persists citations through the user-scoped client (same pattern as
    # chat_messages), so it needs an INSERT policy scoped to threads the user owns.
    op.execute(
        "CREATE POLICY message_citations_owner_insert ON message_citations "
        "FOR INSERT WITH CHECK ("
        "  EXISTS ("
        "    SELECT 1 FROM chat_messages"
        "    JOIN chat_threads ON chat_threads.id = chat_messages.thread_id"
        "    WHERE chat_messages.id = message_citations.message_id"
        "    AND chat_threads.user_id = auth.uid()"
        "  )"
        ")"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY IF EXISTS message_citations_owner_insert ON message_citations")
