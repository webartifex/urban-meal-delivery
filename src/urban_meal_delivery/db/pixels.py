"""Provide the ORM's `Pixel` model."""

import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery.db import meta


class Pixel(meta.Base):
    """A pixel in a `Grid`.

    Square pixels aggregate `Address` objects within a `City`.
    Every `Address` belongs to exactly one `Pixel` in a `Grid`.

    Every `Pixel` has a unique "coordinate" within the `Grid`.
    """

    __tablename__ = 'pixels'

    # Columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)  # noqa:WPS125
    grid_id = sa.Column(sa.SmallInteger, nullable=False, index=True)
    n_x = sa.Column(sa.SmallInteger, nullable=False, index=True)
    n_y = sa.Column(sa.SmallInteger, nullable=False, index=True)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['grid_id'], ['grids.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.CheckConstraint('0 <= n_x', name='n_x_is_positive'),
        sa.CheckConstraint('0 <= n_y', name='n_y_is_positive'),
        # Needed by a `ForeignKeyConstraint` in `AddressPixelAssociation`.
        sa.UniqueConstraint('id', 'grid_id'),
        # Each coordinate within the same `grid` is used at most once.
        sa.UniqueConstraint('grid_id', 'n_x', 'n_y'),
    )

    # Relationships
    grid = orm.relationship('Grid', back_populates='pixels')
    addresses = orm.relationship('AddressPixelAssociation', back_populates='pixel')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}: ({x}, {y})>'.format(
            cls=self.__class__.__name__, x=self.n_x, y=self.n_y,
        )

    # Convenience properties

    @property
    def side_length(self) -> int:
        """The length of one side of a pixel in meters."""
        return self.grid.side_length

    @property
    def area(self) -> float:
        """The area of a pixel in square kilometers."""
        return self.grid.pixel_area
