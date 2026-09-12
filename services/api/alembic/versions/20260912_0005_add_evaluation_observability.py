"""Add evaluation runs and observability audit events.

Revision ID: 20260912_0005
Revises: 20260912_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0005"
down_revision: str | None = "20260912_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rag_runs",
        sa.Column("trace_id", sa.String(length=32), server_default="", nullable=False),
    )
    op.execute("UPDATE rag_runs SET trace_id = md5(id::text) WHERE trace_id = ''")
    op.alter_column("rag_runs", "trace_id", server_default=None)
    op.add_column(
        "rag_runs",
        sa.Column(
            "observability_status",
            sa.String(length=24),
            server_default="disabled",
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_rag_runs_trace_id"), "rag_runs", ["trace_id"], unique=False)

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("rag_run_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("evaluation_type", sa.String(length=32), nullable=False),
        sa.Column("evaluator", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rag_run_id"], ["rag_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_runs_batch_id"),
        "evaluation_runs",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_document_id"),
        "evaluation_runs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_runs_rag_run_id"),
        "evaluation_runs",
        ["rag_run_id"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("rag_run_id", sa.Uuid(), nullable=False),
        sa.Column("event_name", sa.String(length=96), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "payload",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.Column("export_status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rag_run_id"], ["rag_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_events_document_id"),
        "audit_events",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_rag_run_id"),
        "audit_events",
        ["rag_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_events_trace_id"),
        "audit_events",
        ["trace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_trace_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_rag_run_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_document_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(op.f("ix_evaluation_runs_rag_run_id"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_document_id"), table_name="evaluation_runs")
    op.drop_index(op.f("ix_evaluation_runs_batch_id"), table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_index(op.f("ix_rag_runs_trace_id"), table_name="rag_runs")
    op.drop_column("rag_runs", "observability_status")
    op.drop_column("rag_runs", "trace_id")
