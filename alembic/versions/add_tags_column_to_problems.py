from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '001_add_tags_column'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('problems', sa.Column('tags', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('problems', 'tags')