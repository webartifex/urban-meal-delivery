"""Store actuals with forecast.

Revision: #c2af85bada01 at 2021-01-29 11:13:15
Revises: #e86290e7305e
"""

import os

import sqlalchemy as sa
from alembic import op

from urban_meal_delivery import configuration


revision = 'c2af85bada01'
down_revision = 'e86290e7305e'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision c2af85bada01."""
    op.add_column(
        'forecasts',
        sa.Column('actual', sa.SmallInteger(), nullable=False),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ck_forecasts_on_actuals_must_be_non_negative'),
        'forecasts',
        'actual >= 0',
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision e86290e7305e."""
    op.drop_column('forecasts', 'actual', schema=config.CLEAN_SCHEMA)
