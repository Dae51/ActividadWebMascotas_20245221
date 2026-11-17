"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-17
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PET_STATUS = ("active", "pending", "adopted")
ADOPTION_STATUS = ("pending", "approved", "rejected", "completed")
NOTIFICATION_TYPE = (
    "adoption_request",
    "adoption_approved",
    "adoption_rejected",
    "adoption_completed",
    "general",
)


def upgrade() -> None:
    op.execute("CREATE TYPE petstatus AS ENUM ('active', 'pending', 'adopted')")
    op.execute(
        "CREATE TYPE adoptionstatus AS ENUM "
        "('pending', 'approved', 'rejected', 'completed')"
    )
    op.execute(
        "CREATE TYPE notificationtype AS ENUM "
        "('adoption_request', 'adoption_approved', 'adoption_rejected', "
        "'adoption_completed', 'general')"
    )

    pet_status = postgresql.ENUM(*PET_STATUS, name="petstatus", create_type=False)
    adoption_status = postgresql.ENUM(
        *ADOPTION_STATUS, name="adoptionstatus", create_type=False
    )
    notification_type = postgresql.ENUM(
        *NOTIFICATION_TYPE, name="notificationtype", create_type=False
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("email", sa.String(length=100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "pets",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("species", sa.String(length=50), nullable=False),
        sa.Column("breed", sa.String(length=100), nullable=True),
        sa.Column("age_years", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column(
            "is_for_adoption", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("status", pet_status, nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_pet_owner",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )

    op.create_table(
        "adoptions",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("pet_id", sa.Integer(), nullable=False),
        sa.Column("adopter_id", sa.Integer(), nullable=False),
        sa.Column("previous_owner_id", sa.Integer(), nullable=False),
        sa.Column("status", adoption_status, nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pet_id"],
            ["pets.id"],
            name="fk_adoption_pet",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["adopter_id"],
            ["users.id"],
            name="fk_adoption_adopter",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_owner_id"],
            ["users.id"],
            name="fk_adoption_prev_owner",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", notification_type, nullable=False, server_default="general"),
        sa.Column(
            "is_read", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("related_pet_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notif_user",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_pet_id"],
            ["pets.id"],
            name="fk_notif_pet",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
    )

    op.create_index("idx_pets_owner", "pets", ["owner_id"])
    op.create_index("idx_pets_adoption", "pets", ["is_for_adoption", "status"])
    op.create_index("idx_adoptions_pet", "adoptions", ["pet_id", "status"])
    op.create_index("idx_adoptions_adopter", "adoptions", ["adopter_id"])
    op.create_index("idx_notif_user_unread", "notifications", ["user_id", "is_read"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("adoptions")
    op.drop_table("pets")
    op.drop_table("users")

    op.execute("DROP TYPE notificationtype")
    op.execute("DROP TYPE adoptionstatus")
    op.execute("DROP TYPE petstatus")
