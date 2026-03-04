from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "005_add_problem_votes_table"
down_revision = "004_add_problem_created_by_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "problem_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("vote", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("vote IN (1, -1)", name="ck_problem_votes_vote"),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "problem_id", name="uq_problem_votes_user_problem"),
    )
    op.create_index("ix_problem_votes_id", "problem_votes", ["id"], unique=False)
    op.create_index("ix_problem_votes_user_id", "problem_votes", ["user_id"], unique=False)
    op.create_index("ix_problem_votes_problem_id", "problem_votes", ["problem_id"], unique=False)


def downgrade():
    op.drop_index("ix_problem_votes_problem_id", table_name="problem_votes")
    op.drop_index("ix_problem_votes_user_id", table_name="problem_votes")
    op.drop_index("ix_problem_votes_id", table_name="problem_votes")
    op.drop_table("problem_votes")
