"""Rename `Forecast.training_horizon` into `.train_horizon`.

Revision: #8bfb928a31f8 at 2021-02-02 12:55:09
Revises: #c2af85bada01
"""

import os

from alembic import op

from urban_meal_delivery import configuration


revision = '8bfb928a31f8'
down_revision = 'c2af85bada01'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision 8bfb928a31f8."""
    op.execute(
        f"""
        ALTER TABLE
            {config.CLEAN_SCHEMA}.forecasts
        RENAME COLUMN
            training_horizon
            TO
            train_horizon;
        """,
    )  # noqa:WPS355


def downgrade():
    """Downgrade to revision c2af85bada01."""
    op.execute(
        f"""
        ALTER TABLE
            {config.CLEAN_SCHEMA}.forecasts
        RENAME COLUMN
            train_horizon
            TO
            training_horizon;
        """,
    )  # noqa:WPS355
