"""Add demand forecasting.

Revision: #e40623e10405 at 2021-01-06 19:55:56
Revises: #888e352d7526
"""

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from urban_meal_delivery import configuration


revision = 'e40623e10405'
down_revision = '888e352d7526'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision e40623e10405."""
    op.create_table(
        'forecasts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pixel_id', sa.Integer(), nullable=False),
        sa.Column('start_at', sa.DateTime(), nullable=False),
        sa.Column('time_step', sa.SmallInteger(), nullable=False),
        sa.Column('training_horizon', sa.SmallInteger(), nullable=False),
        sa.Column('method', sa.Unicode(length=20), nullable=False),  # noqa:WPS432
        sa.Column('prediction', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_forecasts')),
        sa.ForeignKeyConstraint(
            ['pixel_id'],
            [f'{config.CLEAN_SCHEMA}.pixels.id'],
            name=op.f('fk_forecasts_to_pixels_via_pixel_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    EXTRACT(HOUR FROM start_at) < 11
                    OR
                    EXTRACT(HOUR FROM start_at) > 22
                )
            """,
            name=op.f('ck_forecasts_on_start_at_must_be_within_operating_hours'),
        ),
        sa.CheckConstraint(
            'CAST(EXTRACT(MINUTES FROM start_at) AS INTEGER) % 15 = 0',
            name=op.f('ck_forecasts_on_start_at_minutes_must_be_quarters_of_the_hour'),
        ),
        sa.CheckConstraint(
            'CAST(EXTRACT(MICROSECONDS FROM start_at) AS INTEGER) % 1000000 = 0',
            name=op.f('ck_forecasts_on_start_at_allows_no_microseconds'),
        ),
        sa.CheckConstraint(
            'EXTRACT(SECONDS FROM start_at) = 0',
            name=op.f('ck_forecasts_on_start_at_allows_no_seconds'),
        ),
        sa.CheckConstraint(
            'time_step > 0', name=op.f('ck_forecasts_on_time_step_must_be_positive'),
        ),
        sa.CheckConstraint(
            'training_horizon > 0',
            name=op.f('ck_forecasts_on_training_horizon_must_be_positive'),
        ),
        sa.UniqueConstraint(
            'pixel_id',
            'start_at',
            'time_step',
            'training_horizon',
            'method',
            name=op.f(
                'uq_forecasts_on_pixel_id_start_at_time_step_training_horizon_method',
            ),
        ),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_forecasts_on_pixel_id'),
        'forecasts',
        ['pixel_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision 888e352d7526."""
    op.drop_table('forecasts', schema=config.CLEAN_SCHEMA)
