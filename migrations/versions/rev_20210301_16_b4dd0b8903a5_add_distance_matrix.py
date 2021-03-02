"""Add distance matrix.

Revision: #b4dd0b8903a5 at 2021-03-01 16:14:06
Revises: #8bfb928a31f8
"""

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from urban_meal_delivery import configuration


revision = 'b4dd0b8903a5'
down_revision = '8bfb928a31f8'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision b4dd0b8903a5."""
    op.create_table(
        'addresses_addresses',
        sa.Column('first_address_id', sa.Integer(), nullable=False),
        sa.Column('second_address_id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.SmallInteger(), nullable=False),
        sa.Column('air_distance', sa.Integer(), nullable=False),
        sa.Column('bicycle_distance', sa.Integer(), nullable=True),
        sa.Column('bicycle_duration', sa.Integer(), nullable=True),
        sa.Column('directions', postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint(
            'first_address_id',
            'second_address_id',
            name=op.f('pk_addresses_addresses'),
        ),
        sa.ForeignKeyConstraint(
            ['first_address_id', 'city_id'],
            [
                f'{config.CLEAN_SCHEMA}.addresses.id',
                f'{config.CLEAN_SCHEMA}.addresses.city_id',
            ],
            name=op.f(
                'fk_addresses_addresses_to_addresses_via_first_address_id_city_id',
            ),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['second_address_id', 'city_id'],
            [
                f'{config.CLEAN_SCHEMA}.addresses.id',
                f'{config.CLEAN_SCHEMA}.addresses.city_id',
            ],
            name=op.f(
                'fk_addresses_addresses_to_addresses_via_second_address_id_city_id',
            ),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.UniqueConstraint(
            'first_address_id',
            'second_address_id',
            name=op.f('uq_addresses_addresses_on_first_address_id_second_address_id'),
        ),
        sa.CheckConstraint(
            'first_address_id < second_address_id',
            name=op.f('ck_addresses_addresses_on_distances_are_symmetric_for_bicycles'),
        ),
        sa.CheckConstraint(
            '0 <= air_distance AND air_distance < 20000',
            name=op.f('ck_addresses_addresses_on_realistic_air_distance'),
        ),
        sa.CheckConstraint(
            'bicycle_distance < 25000',
            name=op.f('ck_addresses_addresses_on_realistic_bicycle_distance'),
        ),
        sa.CheckConstraint(
            'air_distance <= bicycle_distance',
            name=op.f('ck_addresses_addresses_on_air_distance_is_shortest'),
        ),
        sa.CheckConstraint(
            '0 <= bicycle_duration AND bicycle_duration <= 3600',
            name=op.f('ck_addresses_addresses_on_realistic_bicycle_travel_time'),
        ),
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision 8bfb928a31f8."""
    op.drop_table('addresses_addresses', schema=config.CLEAN_SCHEMA)
