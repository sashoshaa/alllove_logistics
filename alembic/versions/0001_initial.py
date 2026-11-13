"""Начальная схема AllLove Logistics 1.0.0.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="client"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("contact", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=True)

    op.create_table(
        "storage_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_storage_locations_name", "storage_locations", ["name"])

    op.create_table(
        "catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("size", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_catalog_items_sku", "catalog_items", ["sku"], unique=True)

    op.create_table(
        "supplies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("storage_locations.id"), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column("responsible_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_supplies_id", "supplies", ["id"])
    op.create_index("ix_supplies_number", "supplies", ["number"], unique=True)
    op.create_index("ix_supplies_status", "supplies", ["status"])

    op.create_table(
        "supply_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("planned_qty", sa.Integer(), nullable=False),
        sa.Column("actual_qty", sa.Integer(), nullable=True),
    )

    op.create_table(
        "supply_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "supply_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("validator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "discrepancies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("supply_items.id"), nullable=False),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("supply_checks.id"), nullable=False),
        sa.Column("planned_qty", sa.Integer(), nullable=False),
        sa.Column("actual_qty", sa.Integer(), nullable=False),
        sa.Column("difference", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
    )

    op.create_table(
        "change_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "supply_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("object_type", sa.String(), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_object_type", "audit_events", ["object_type"])

    op.create_table(
        "supply_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), sa.ForeignKey("supplies.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("field", sa.String(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_supply_history_supply_id", "supply_history", ["supply_id"])


def downgrade() -> None:
    op.drop_table("supply_history")
    op.drop_table("audit_events")
    op.drop_table("notifications")
    op.drop_table("supply_comments")
    op.drop_table("change_proposals")
    op.drop_table("discrepancies")
    op.drop_table("supply_checks")
    op.drop_table("supply_documents")
    op.drop_table("supply_items")
    op.drop_table("supplies")
    op.drop_table("catalog_items")
    op.drop_table("storage_locations")
    op.drop_table("suppliers")
    op.drop_table("users")
