"""Initial schema with all 7 tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-15 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Tables are verified and managed by db.create_all() and Alembic
    pass


def downgrade():
    op.drop_table('monitoring_logs')
    op.drop_table('policy_analyses')
    op.drop_table('policy_changes')
    op.drop_table('document_versions')
    op.drop_table('policy_documents')
    op.drop_table('policy_categories')
    op.drop_table('government_sources')
