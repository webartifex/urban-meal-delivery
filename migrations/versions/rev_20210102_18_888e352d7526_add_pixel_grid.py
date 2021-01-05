"""Add pixel grid.

Revision: #888e352d7526 at 2021-01-02 18:11:02
Revises: #f11cd76d2f45
"""

import os

import sqlalchemy as sa
from alembic import op

from urban_meal_delivery import configuration


revision = '888e352d7526'
down_revision = 'f11cd76d2f45'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision 888e352d7526."""
    op.create_table(
        'grids',
        sa.Column('id', sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column('city_id', sa.SmallInteger(), nullable=False),
        sa.Column('side_length', sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_grids')),
        sa.ForeignKeyConstraint(
            ['city_id'],
            [f'{config.CLEAN_SCHEMA}.cities.id'],
            name=op.f('fk_grids_to_cities_via_city_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.UniqueConstraint(
            'city_id', 'side_length', name=op.f('uq_grids_on_city_id_side_length'),
        ),
        # This `UniqueConstraint` is needed by the `addresses_pixels` table below.
        sa.UniqueConstraint('id', 'city_id', name=op.f('uq_grids_on_id_city_id')),
        schema=config.CLEAN_SCHEMA,
    )

    op.create_table(
        'pixels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('grid_id', sa.SmallInteger(), nullable=False),
        sa.Column('n_x', sa.SmallInteger(), nullable=False),
        sa.Column('n_y', sa.SmallInteger(), nullable=False),
        sa.CheckConstraint('0 <= n_x', name=op.f('ck_pixels_on_n_x_is_positive')),
        sa.CheckConstraint('0 <= n_y', name=op.f('ck_pixels_on_n_y_is_positive')),
        sa.ForeignKeyConstraint(
            ['grid_id'],
            [f'{config.CLEAN_SCHEMA}.grids.id'],
            name=op.f('fk_pixels_to_grids_via_grid_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pixels')),
        sa.UniqueConstraint(
            'grid_id', 'n_x', 'n_y', name=op.f('uq_pixels_on_grid_id_n_x_n_y'),
        ),
        sa.UniqueConstraint('id', 'grid_id', name=op.f('uq_pixels_on_id_grid_id')),
        schema=config.CLEAN_SCHEMA,
    )

    op.create_index(
        op.f('ix_pixels_on_grid_id'),
        'pixels',
        ['grid_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_pixels_on_n_x'),
        'pixels',
        ['n_x'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_pixels_on_n_y'),
        'pixels',
        ['n_y'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )

    # This `UniqueConstraint` is needed by the `addresses_pixels` table below.
    op.create_unique_constraint(
        'uq_addresses_on_id_city_id',
        'addresses',
        ['id', 'city_id'],
        schema=config.CLEAN_SCHEMA,
    )

    op.create_table(
        'addresses_pixels',
        sa.Column('address_id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.SmallInteger(), nullable=False),
        sa.Column('grid_id', sa.SmallInteger(), nullable=False),
        sa.Column('pixel_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['address_id', 'city_id'],
            [
                f'{config.CLEAN_SCHEMA}.addresses.id',
                f'{config.CLEAN_SCHEMA}.addresses.city_id',
            ],
            name=op.f('fk_addresses_pixels_to_addresses_via_address_id_city_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['grid_id', 'city_id'],
            [
                f'{config.CLEAN_SCHEMA}.grids.id',
                f'{config.CLEAN_SCHEMA}.grids.city_id',
            ],
            name=op.f('fk_addresses_pixels_to_grids_via_grid_id_city_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['pixel_id', 'grid_id'],
            [
                f'{config.CLEAN_SCHEMA}.pixels.id',
                f'{config.CLEAN_SCHEMA}.pixels.grid_id',
            ],
            name=op.f('fk_addresses_pixels_to_pixels_via_pixel_id_grid_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint(
            'address_id', 'pixel_id', name=op.f('pk_addresses_pixels'),
        ),
        sa.UniqueConstraint(
            'address_id',
            'grid_id',
            name=op.f('uq_addresses_pixels_on_address_id_grid_id'),
        ),
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision f11cd76d2f45."""
    op.drop_table('addresses_pixels', schema=config.CLEAN_SCHEMA)
    op.drop_index(
        op.f('ix_pixels_on_n_y'), table_name='pixels', schema=config.CLEAN_SCHEMA,
    )
    op.drop_index(
        op.f('ix_pixels_on_n_x'), table_name='pixels', schema=config.CLEAN_SCHEMA,
    )
    op.drop_index(
        op.f('ix_pixels_on_grid_id'), table_name='pixels', schema=config.CLEAN_SCHEMA,
    )
    op.drop_table('pixels', schema=config.CLEAN_SCHEMA)
    op.drop_table('grids', schema=config.CLEAN_SCHEMA)
