"""Add document validation, official URL, and classification fields

Revision ID: 002_add_document_validation_fields
Revises: 001_initial_schema
Create Date: 2026-11-15 18:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_document_validation_fields'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Add new validation and tracking columns to policy_documents table
    with op.batch_alter_table('policy_documents') as batch_op:
        batch_op.add_column(sa.Column('official_url', sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column('source_listing_url', sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column('first_detected_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('current_version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('classification_status', sa.String(length=50), nullable=False, server_default='verified_policy'))


def downgrade():
    with op.batch_alter_table('policy_documents') as batch_op:
        batch_op.drop_column('classification_status')
        batch_op.drop_column('is_verified')
        batch_op.drop_column('current_version')
        batch_op.drop_column('first_detected_at')
        batch_op.drop_column('source_listing_url')
        batch_op.drop_column('official_url')
