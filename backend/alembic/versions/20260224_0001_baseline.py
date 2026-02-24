"""baseline schema with checkpoints

Revision ID: 20260224_0001
Revises:
Create Date: 2026-02-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260224_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("PRAGMA journal_mode=WAL;")

    op.create_table(
        "runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("model_runtime", sa.Text(), nullable=False),
        sa.Column("disease_track", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_table(
        "patients",
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), primary_key=True),
        sa.Column("patient_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("chunk_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "protocols",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("protocol_id", sa.Text(), nullable=False),
        sa.Column("rank_seed", sa.Float(), nullable=True),
        sa.Column("protocol_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "coarse_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("protocol_id", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "daily_states",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("protocol_id", sa.Text(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "safety_flags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("protocol_id", sa.Text(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("disqualifying", sa.Integer(), nullable=False),
    )
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("protocol_id", sa.Text(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("component_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("protocol_id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
    )
    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
    )
    op.create_table(
        "run_results",
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), primary_key=True),
        sa.Column("result_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "run_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("node_name", sa.Text(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("run_checkpoints")
    op.drop_table("run_results")
    op.drop_table("run_events")
    op.drop_table("chat_logs")
    op.drop_table("citations")
    op.drop_table("scores")
    op.drop_table("safety_flags")
    op.drop_table("daily_states")
    op.drop_table("coarse_results")
    op.drop_table("protocols")
    op.drop_table("evidence")
    op.drop_table("patients")
    op.drop_table("runs")

