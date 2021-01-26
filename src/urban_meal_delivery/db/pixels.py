"""Provide the ORM's `Pixel` model."""

import sqlalchemy as sa
import utm
from sqlalchemy import orm

from urban_meal_delivery.db import meta
from urban_meal_delivery.db import utils


class Pixel(meta.Base):
    """A pixel in a `Grid`.

    Square pixels aggregate `Address` objects within a `City`.
    Every `Address` belongs to exactly one `Pixel` in a `Grid`.

    Every `Pixel` has a unique `n_x`-`n_y` coordinate within the `Grid`.
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
    forecasts = orm.relationship('Forecast', back_populates='pixel')

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

    @property
    def northeast(self) -> utils.Location:
        """The pixel's northeast corner, relative to `.grid.city.southwest`.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_northeast'):  # noqa:WPS421  note:d334120e
            # The origin is the southwest corner of the `.grid.city`'s viewport.
            easting_origin = self.grid.city.southwest.easting
            northing_origin = self.grid.city.southwest.northing

            # `+1` as otherwise we get the pixel's `.southwest` corner.
            easting = easting_origin + ((self.n_x + 1) * self.side_length)
            northing = northing_origin + ((self.n_y + 1) * self.side_length)
            zone, band = self.grid.city.southwest.zone_details
            latitude, longitude = utm.to_latlon(easting, northing, zone, band)

            self._northeast = utils.Location(latitude, longitude)
            self._northeast.relate_to(self.grid.city.southwest)

        return self._northeast

    @property
    def southwest(self) -> utils.Location:
        """The pixel's northeast corner, relative to `.grid.city.southwest`.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_southwest'):  # noqa:WPS421  note:d334120e
            # The origin is the southwest corner of the `.grid.city`'s viewport.
            easting_origin = self.grid.city.southwest.easting
            northing_origin = self.grid.city.southwest.northing

            easting = easting_origin + (self.n_x * self.side_length)
            northing = northing_origin + (self.n_y * self.side_length)
            zone, band = self.grid.city.southwest.zone_details
            latitude, longitude = utm.to_latlon(easting, northing, zone, band)

            self._southwest = utils.Location(latitude, longitude)
            self._southwest.relate_to(self.grid.city.southwest)

        return self._southwest
