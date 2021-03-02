"""Model for the many-to-many relationship between `Address` and `Pixel` objects."""

import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery.db import meta


class AddressPixelAssociation(meta.Base):
    """Association pattern between `Address` and `Pixel`.

    This approach is needed here mainly because it implicitly
    updates the `city_id` and `grid_id` columns.

    Further info:
        https://docs.sqlalchemy.org/en/stable/orm/basic_relationships.html#association-object  # noqa:E501
    """

    __tablename__ = 'addresses_pixels'

    # Columns
    address_id = sa.Column(sa.Integer, primary_key=True)
    city_id = sa.Column(sa.SmallInteger, nullable=False)
    grid_id = sa.Column(sa.SmallInteger, nullable=False)
    pixel_id = sa.Column(sa.Integer, primary_key=True)

    # Constraints
    __table_args__ = (
        # An `Address` can only be on a `Grid` ...
        sa.ForeignKeyConstraint(
            ['address_id', 'city_id'],
            ['addresses.id', 'addresses.city_id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        # ... if their `.city` attributes match.
        sa.ForeignKeyConstraint(
            ['grid_id', 'city_id'],
            ['grids.id', 'grids.city_id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        # Each `Address` can only be on a `Grid` once.
        sa.UniqueConstraint('address_id', 'grid_id'),
        # An association must reference an existing `Grid`-`Pixel` pair.
        sa.ForeignKeyConstraint(
            ['pixel_id', 'grid_id'],
            ['pixels.id', 'pixels.grid_id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
    )

    # Relationships
    address = orm.relationship('Address', back_populates='pixels')
    pixel = orm.relationship('Pixel', back_populates='addresses')
