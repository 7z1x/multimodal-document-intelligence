"""Add document processing and structured extraction tables.

Revision ID: 20260912_0002
Revises: 20260912_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0002"
down_revision: str | None = "20260912_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "documents",
        "status",
        existing_type=sa.String(length=10),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.add_column("documents", sa.Column("error_code", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_table(
        "document_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_number"),
    )
    op.create_index(
        op.f("ix_document_pages_document_id"),
        "document_pages",
        ["document_id"],
        unique=False,
    )
    op.create_table(
        "invoice_extractions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("backend", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("is_math_valid", sa.Boolean(), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invoice_extractions_document_id"),
        "invoice_extractions",
        ["document_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_extractions_document_id"), table_name="invoice_extractions")
    op.drop_table("invoice_extractions")
    op.drop_index(op.f("ix_document_pages_document_id"), table_name="document_pages")
    op.drop_table("document_pages")
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "error_code")
    op.execute("UPDATE documents SET status = 'STORED' WHERE length(status) > 10")
    op.alter_column(
        "documents",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
