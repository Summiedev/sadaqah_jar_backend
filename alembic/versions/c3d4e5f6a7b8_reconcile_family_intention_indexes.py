"""reconcile indexes declared on family intention models"""

from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These indexes already exist in the ORM metadata but were omitted from
    # the original family-intentions migration. They are additive and do not
    # rewrite or remove any existing user data.
    op.create_index(
        "ix_family_intention_contributions_user_id",
        "family_intention_contributions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_family_intentions_created_by",
        "family_intentions",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "ix_family_intentions_deleted_at",
        "family_intentions",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_family_intentions_deleted_at", table_name="family_intentions"
    )
    op.drop_index(
        "ix_family_intentions_created_by", table_name="family_intentions"
    )
    op.drop_index(
        "ix_family_intention_contributions_user_id",
        table_name="family_intention_contributions",
    )
