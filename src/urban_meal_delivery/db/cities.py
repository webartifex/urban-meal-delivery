"""Provide the ORM's `City` model."""

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery.db import meta
from urban_meal_delivery.db import utils


class City(meta.Base):
    """A city where the UDP operates in."""

    __tablename__ = 'cities'

    # Generic columns
    id = sa.Column(  # noqa:WPS125
        sa.SmallInteger, primary_key=True, autoincrement=False,
    )
    name = sa.Column(sa.Unicode(length=10), nullable=False)
    kml = sa.Column(sa.UnicodeText, nullable=False)

    # Google Maps related columns
    center_latitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    center_longitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    northeast_latitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    northeast_longitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    southwest_latitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    southwest_longitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    initial_zoom = sa.Column(sa.SmallInteger, nullable=False)

    # Relationships
    addresses = orm.relationship('Address', back_populates='city')
    grids = orm.relationship('Grid', back_populates='city')

    # We do not implement a `.__init__()` method and leave that to SQLAlchemy.
    # Instead, we use `hasattr()` to check for uninitialized attributes.  grep:d334120e

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({name})>'.format(cls=self.__class__.__name__, name=self.name)

    @property
    def center(self) -> utils.Location:
        """Location of the city's center.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_center'):  # noqa:WPS421  note:d334120e
            self._center = utils.Location(self.center_latitude, self.center_longitude)
        return self._center

    @property
    def northeast(self) -> utils.Location:
        """The city's northeast corner of the Google Maps viewport.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_northeast'):  # noqa:WPS421  note:d334120e
            self._northeast = utils.Location(
                self.northeast_latitude, self.northeast_longitude,
            )

        return self._northeast

    @property
    def southwest(self) -> utils.Location:
        """The city's southwest corner of the Google Maps viewport.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_southwest'):  # noqa:WPS421  note:d334120e
            self._southwest = utils.Location(
                self.southwest_latitude, self.southwest_longitude,
            )

        return self._southwest

    @property
    def total_x(self) -> int:
        """The horizontal distance from the city's west to east end in meters.

        The city borders refer to the Google Maps viewport.
        """
        return self.northeast.easting - self.southwest.easting

    @property
    def total_y(self) -> int:
        """The vertical distance from the city's south to north end in meters.

        The city borders refer to the Google Maps viewport.
        """
        return self.northeast.northing - self.southwest.northing
