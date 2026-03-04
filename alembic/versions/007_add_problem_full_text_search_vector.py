from alembic import op

# revision identifiers, used by Alembic
revision = "007_add_problem_full_text_search_vector"
down_revision = "006_add_tags_and_problem_tags"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE problems ADD COLUMN IF NOT EXISTS search_vector tsvector")
    op.execute(
        """
        UPDATE problems
        SET search_vector = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_problems_search_vector_gin
        ON problems
        USING GIN (search_vector)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION problems_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                to_tsvector('english', coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_problems_search_vector_update ON problems;
        CREATE TRIGGER trg_problems_search_vector_update
        BEFORE INSERT OR UPDATE ON problems
        FOR EACH ROW EXECUTE FUNCTION problems_search_vector_update();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_problems_search_vector_update ON problems")
    op.execute("DROP FUNCTION IF EXISTS problems_search_vector_update")
    op.execute("DROP INDEX IF EXISTS ix_problems_search_vector_gin")
    op.execute("ALTER TABLE problems DROP COLUMN IF EXISTS search_vector")
