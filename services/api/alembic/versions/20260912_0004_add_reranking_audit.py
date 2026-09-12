"""Add reranking and citation verification audit fields.

Revision ID: 20260912_0004
Revises: 20260912_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0004"
down_revision: str | None = "20260912_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rag_runs",
        sa.Column(
            "retrieval_trace",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "rag_runs",
        sa.Column(
            "citation_support_score",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "rag_runs",
        sa.Column(
            "citation_errors",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("rag_runs", "citation_errors")
    op.drop_column("rag_runs", "citation_support_score")
    op.drop_column("rag_runs", "retrieval_trace")
