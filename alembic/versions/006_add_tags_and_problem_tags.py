from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "006_add_tags_and_problem_tags"
down_revision = "005_add_problem_votes_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_id", "tags", ["id"], unique=False)
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "problem_tags",
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["problems.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("problem_id", "tag_id"),
        sa.UniqueConstraint("problem_id", "tag_id", name="uq_problem_tags_problem_tag"),
    )


def downgrade():
    op.drop_table("problem_tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_index("ix_tags_id", table_name="tags")
    op.drop_table("tags")
