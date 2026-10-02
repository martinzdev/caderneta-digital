"""initial schema

Revision ID: 8308bdcddd76
Revises:
Create Date: 2026-10-02 12:53:58.166412

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8308bdcddd76"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=11), nullable=True),
        sa.Column("address", sa.String(length=200), nullable=True),
        sa.Column("credit_limit", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("credit_limit >= 0", name="ck_client_limit"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_clients_name"), ["name"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("login", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=100), nullable=False),
        sa.Column("role", sa.Enum("owner", "staff", name="role"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_login"), ["login"], unique=True)

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("method", sa.Enum("cash", "pix", "card", name="paymentmethod"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("canceled", sa.Boolean(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount"),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_payments_client_id"), ["client_id"], unique=False)

    op.create_table(
        "purchases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("description", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("canceled", sa.Boolean(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_purchase_amount"),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_purchases_client_id"), ["client_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_refresh_tokens_user_id"), ["user_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("items", sa.String(length=500), nullable=False),
        sa.Column("address", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum("new", "packed", "delivered", "canceled", name="orderstatus"),
            nullable=False,
        ),
        sa.Column("payment", sa.Enum("tab", "on_delivery", name="orderpayment"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("purchase_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_orders_client_id"), ["client_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_orders_client_id"))

    op.drop_table("orders")
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_refresh_tokens_user_id"))

    op.drop_table("refresh_tokens")
    with op.batch_alter_table("purchases", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purchases_client_id"))

    op.drop_table("purchases")
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_payments_client_id"))

    op.drop_table("payments")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_login"))

    op.drop_table("users")
    with op.batch_alter_table("clients", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_clients_name"))

    op.drop_table("clients")
