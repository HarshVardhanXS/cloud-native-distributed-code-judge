from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "002_normalize_problem_testcase_submission"
down_revision = "001_create_problems_table"
branch_labels = None
depends_on = None


STATUS_ENUM = sa.Enum(
    "queued",
    "running",
    "accepted",
    "wrong_answer",
    "error",
    name="submission_status",
    native_enum=False,
)


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("username", sa.String, nullable=False, unique=True),
            sa.Column("email", sa.String, nullable=False, unique=True),
            sa.Column("hashed_password", sa.String, nullable=False),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_users_id", "users", ["id"], unique=False)
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    problem_cols = _column_names(inspector, "problems")
    with op.batch_alter_table("problems") as batch:
        if "tags" in problem_cols:
            batch.drop_column("tags")
        if "test_cases" in problem_cols:
            batch.drop_column("test_cases")
        if "creator_id" in problem_cols:
            batch.drop_column("creator_id")
        if "updated_at" in problem_cols:
            batch.drop_column("updated_at")

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "testcases"):
        op.create_table(
            "testcases",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "problem_id",
                sa.Integer,
                sa.ForeignKey("problems.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("input_data", sa.Text, nullable=False),
            sa.Column("expected_output", sa.Text, nullable=False),
        )
        op.create_index("ix_testcases_id", "testcases", ["id"], unique=False)

    inspector = sa.inspect(bind)
    testcase_indexes = _index_names(inspector, "testcases")
    if "ix_testcases_problem_id" not in testcase_indexes:
        op.create_index("ix_testcases_problem_id", "testcases", ["problem_id"], unique=False)

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "submissions"):
        op.create_table(
            "submissions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("problem_id", sa.Integer, sa.ForeignKey("problems.id"), nullable=False),
            sa.Column("code", sa.Text, nullable=False),
            sa.Column("status", STATUS_ENUM, nullable=False, server_default="queued"),
            sa.Column("runtime_ms", sa.Integer, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False),
        )
        op.create_index("ix_submissions_id", "submissions", ["id"], unique=False)
    else:
        submission_cols = _column_names(inspector, "submissions")
        with op.batch_alter_table("submissions") as batch:
            if "result" in submission_cols:
                batch.drop_column("result")
            if "runtime_ms" not in submission_cols:
                batch.add_column(sa.Column("runtime_ms", sa.Integer, nullable=True))
            if "status" in submission_cols:
                batch.alter_column(
                    "status",
                    existing_type=sa.String(),
                    type_=STATUS_ENUM,
                    existing_nullable=False,
                )

    inspector = sa.inspect(bind)
    submission_indexes = _index_names(inspector, "submissions")
    if "ix_submissions_user_id" not in submission_indexes:
        op.create_index("ix_submissions_user_id", "submissions", ["user_id"], unique=False)
    if "ix_submissions_problem_id" not in submission_indexes:
        op.create_index("ix_submissions_problem_id", "submissions", ["problem_id"], unique=False)


def downgrade():
    op.drop_index("ix_submissions_problem_id", table_name="submissions")
    op.drop_index("ix_submissions_user_id", table_name="submissions")
    op.drop_table("submissions")

    op.drop_index("ix_testcases_problem_id", table_name="testcases")
    op.drop_index("ix_testcases_id", table_name="testcases")
    op.drop_table("testcases")

    with op.batch_alter_table("problems") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime, nullable=True))
        batch.add_column(sa.Column("creator_id", sa.Integer, nullable=True))
        batch.add_column(sa.Column("tags", sa.JSON(), nullable=True))

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
