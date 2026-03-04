from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "003_add_problem_type_publish_solution"
down_revision = "002_normalize_problem_testcase_submission"
branch_labels = None
depends_on = None

problem_type_enum = sa.Enum(
    "coding",
    "system_design",
    name="problem_type",
    native_enum=False,
)


def upgrade():
    bind = op.get_bind()
    problem_type_enum.create(bind, checkfirst=True)

    op.add_column(
        "problems",
        sa.Column(
            "type",
            problem_type_enum,
            nullable=False,
            server_default="coding",
        ),
    )
    op.add_column(
        "problems",
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "problems",
        sa.Column("solution_approach", sa.Text(), nullable=True),
    )

    op.create_index("ix_problems_type", "problems", ["type"], unique=False)
    op.create_index(
        "ix_problems_is_published",
        "problems",
        ["is_published"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_problems_is_published", table_name="problems")
    op.drop_index("ix_problems_type", table_name="problems")
    op.drop_column("problems", "solution_approach")
    op.drop_column("problems", "is_published")
    op.drop_column("problems", "type")
    problem_type_enum.drop(op.get_bind(), checkfirst=True)
