from alembic import op
import sqlalchemy as sa

revision = '001_create_problems_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'problems',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('difficulty', sa.String, nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False)
    )

def downgrade():
    op.drop_table('problems')