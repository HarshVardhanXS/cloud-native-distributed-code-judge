from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "004_add_problem_created_by_ownership"
down_revision = "003_add_problem_type_publish_solution"
branch_labels = None
depends_on = None


def _ensure_system_user(bind) -> int:
    user_id = bind.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    if user_id is not None:
        return int(user_id)

    now = datetime.utcnow()
    bind.execute(
        sa.text(
            """
            INSERT INTO users (username, email, hashed_password, created_at, is_active)
            VALUES (:username, :email, :hashed_password, :created_at, :is_active)
            """
        ),
        {
            "username": "system",
            "email": "system@local",
            "hashed_password": "!",
            "created_at": now,
            "is_active": True,
        },
    )
    user_id = bind.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    return int(user_id)


def upgrade():
    bind = op.get_bind()
    creator_id = _ensure_system_user(bind)

    with op.batch_alter_table("problems") as batch:
        batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE problems SET created_by = :creator_id WHERE created_by IS NULL"
        ),
        {"creator_id": creator_id},
    )

    with op.batch_alter_table("problems") as batch:
        batch.alter_column("created_by", nullable=False)
        batch.create_foreign_key(
            "fk_problems_created_by_users",
            "users",
            ["created_by"],
            ["id"],
        )
        batch.create_index("ix_problems_created_by", ["created_by"], unique=False)


def downgrade():
    with op.batch_alter_table("problems") as batch:
        batch.drop_index("ix_problems_created_by")
        batch.drop_constraint("fk_problems_created_by_users", type_="foreignkey")
        batch.drop_column("created_by")
