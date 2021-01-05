"""Provide the ORM's `Grid` model."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery import db
from urban_meal_delivery.db import meta


class Grid(meta.Base):
    """A grid of `Pixel`s to partition a `City`.

    A grid is characterized by the uniform size of the `Pixel`s it contains.
    That is configures via the `Grid.side_length` attribute.
    """

    __tablename__ = 'grids'

    # Columns
    id = sa.Column(  # noqa:WPS125
        sa.SmallInteger, primary_key=True, autoincrement=True,
    )
    _city_id = sa.Column('city_id', sa.SmallInteger, nullable=False)
    side_length = sa.Column(sa.SmallInteger, nullable=False, unique=True)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['city_id'], ['cities.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        # Each `Grid`, characterized by its `.side_length`,
        # may only exists once for a given `.city`.
        sa.UniqueConstraint('city_id', 'side_length'),
        # Needed by a `ForeignKeyConstraint` in `address_pixel_association`.
        sa.UniqueConstraint('id', 'city_id'),
    )

    # Relationships
    city = orm.relationship('City', back_populates='grids')
    pixels = orm.relationship('Pixel', back_populates='grid')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}: {area}>'.format(
            cls=self.__class__.__name__, area=self.pixel_area,
        )

    # Convenience properties
    @property
    def pixel_area(self) -> float:
        """The area of a `Pixel` on the grid in square kilometers."""
        return (self.side_length ** 2) / 1_000_000  # noqa:WPS432

    @classmethod
    def gridify(cls, city: db.City, side_length: int) -> db.Grid:
        """Create a fully populated `Grid` for a `city`.

        The created `Grid` contains only the `Pixel`s for which
        there is at least one `Address` in it.

        Args:
            city: city for which the grid is created
            side_length: the length of a square `Pixel`'s side

        Returns:
            grid: including `grid.pixels` with the associated `city.addresses`
        """
        grid = cls(city=city, side_length=side_length)

        # Create `Pixel` objects covering the entire `city`.
        # Note: `+1` so that `city.northeast` corner is on the grid.
        possible_pixels = [
            db.Pixel(n_x=n_x, n_y=n_y)
            for n_x in range((city.total_x // side_length) + 1)
            for n_y in range((city.total_y // side_length) + 1)
        ]

        # For convenient lookup by `.n_x`-`.n_y` coordinates.
        pixel_map = {(pixel.n_x, pixel.n_y): pixel for pixel in possible_pixels}

        for address in city.addresses:
            # Determine which `pixel` the `address` belongs to.
            n_x = address.x // side_length
            n_y = address.y // side_length
            pixel = pixel_map[n_x, n_y]

            # Create an association between the `address` and `pixel`.
            assoc = db.AddressPixelAssociation(address=address, pixel=pixel)
            pixel.addresses.append(assoc)

        # Only keep `pixel`s that contain at least one `Address`.
        grid.pixels = [pixel for pixel in pixel_map.values() if pixel.addresses]

        return grid
