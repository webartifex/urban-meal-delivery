"""Provide the ORM's `Grid` model."""

import sqlalchemy as sa
from sqlalchemy import orm

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
