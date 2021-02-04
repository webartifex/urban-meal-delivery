"""Add confidence intervals to forecasts.

Revision: #26711cd3f9b9 at 2021-01-20 16:08:21
Revises: #e40623e10405
"""

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from urban_meal_delivery import configuration


revision = '26711cd3f9b9'
down_revision = 'e40623e10405'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision 26711cd3f9b9."""
    op.alter_column(
        'forecasts', 'method', new_column_name='model', schema=config.CLEAN_SCHEMA,
    )
    op.add_column(
        'forecasts',
        sa.Column('low80', postgresql.DOUBLE_PRECISION(), nullable=True),
        schema=config.CLEAN_SCHEMA,
    )
    op.add_column(
        'forecasts',
        sa.Column('high80', postgresql.DOUBLE_PRECISION(), nullable=True),
        schema=config.CLEAN_SCHEMA,
    )
    op.add_column(
        'forecasts',
        sa.Column('low95', postgresql.DOUBLE_PRECISION(), nullable=True),
        schema=config.CLEAN_SCHEMA,
    )
    op.add_column(
        'forecasts',
        sa.Column('high95', postgresql.DOUBLE_PRECISION(), nullable=True),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ck_forecasts_on_ci_upper_and_lower_bounds'),
        'forecasts',
        """
        NOT (
            low80 IS NULL AND high80 IS NOT NULL
            OR
            low80 IS NOT NULL AND high80 IS NULL
            OR
            low95 IS NULL AND high95 IS NOT NULL
            OR
            low95 IS NOT NULL AND high95 IS NULL
        )
        """,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_check_constraint(
        op.f('prediction_must_be_within_ci'),
        'forecasts',
        """
        NOT (
            prediction < low80
            OR
            prediction < low95
            OR
            prediction > high80
            OR
            prediction > high95
        )
        """,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ci_upper_bound_greater_than_lower_bound'),
        'forecasts',
        """
        NOT (
            low80 > high80
            OR
            low95 > high95
        )
        """,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_check_constraint(
        op.f('ci95_must_be_wider_than_ci80'),
        'forecasts',
        """
        NOT (
            low80 < low95
            OR
            high80 > high95
        )
        """,
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision e40623e10405."""
    op.alter_column(
        'forecasts', 'model', new_column_name='method', schema=config.CLEAN_SCHEMA,
    )
    op.drop_column(
        'forecasts', 'low80', schema=config.CLEAN_SCHEMA,
    )
    op.drop_column(
        'forecasts', 'high80', schema=config.CLEAN_SCHEMA,
    )
    op.drop_column(
        'forecasts', 'low95', schema=config.CLEAN_SCHEMA,
    )
    op.drop_column(
        'forecasts', 'high95', schema=config.CLEAN_SCHEMA,
    )
