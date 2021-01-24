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
    city_id = sa.Column(sa.SmallInteger, nullable=False)
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
        return '<{cls}: {area} sqr. km>'.format(
            cls=self.__class__.__name__, area=self.pixel_area,
        )

    # Convenience properties
    @property
    def pixel_area(self) -> float:
        """The area of a `Pixel` on the grid in square kilometers."""
        return round((self.side_length ** 2) / 1_000_000, 1)

    @classmethod
    def gridify(cls, city: db.City, side_length: int) -> db.Grid:
        """Create a fully populated `Grid` for a `city`.

        The `Grid` contains only `Pixel`s that have at least one `Address`.
        `Address` objects outside the `city`'s viewport are discarded.

        Args:
            city: city for which the grid is created
            side_length: the length of a square `Pixel`'s side

        Returns:
            grid: including `grid.pixels` with the associated `city.addresses`
        """
        grid = cls(city=city, side_length=side_length)

        # `Pixel`s grouped by `.n_x`-`.n_y` coordinates.
        pixels = {}

        for address in city.addresses:
            # Check if an `address` is not within the `city`'s viewport, ...
            not_within_city_viewport = (
                address.x < 0
                or address.x > city.total_x
                or address.y < 0
                or address.y > city.total_y
            )
            # ... and, if so, the `address` does not belong to any `Pixel`.
            if not_within_city_viewport:
                continue

            # Determine which `pixel` the `address` belongs to ...
            n_x, n_y = address.x // side_length, address.y // side_length
            # ... and create a new `Pixel` object if necessary.
            if (n_x, n_y) not in pixels:
                pixels[(n_x, n_y)] = db.Pixel(grid=grid, n_x=n_x, n_y=n_y)
            pixel = pixels[(n_x, n_y)]

            # Create an association between the `address` and `pixel`.
            assoc = db.AddressPixelAssociation(address=address, pixel=pixel)
            pixel.addresses.append(assoc)

        return grid
