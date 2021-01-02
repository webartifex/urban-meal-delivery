"""Provide the ORM's `City` model."""

from typing import Any, Dict

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
    _center_latitude = sa.Column(
        'center_latitude', postgresql.DOUBLE_PRECISION, nullable=False,
    )
    _center_longitude = sa.Column(
        'center_longitude', postgresql.DOUBLE_PRECISION, nullable=False,
    )
    _northeast_latitude = sa.Column(
        'northeast_latitude', postgresql.DOUBLE_PRECISION, nullable=False,
    )
    _northeast_longitude = sa.Column(
        'northeast_longitude', postgresql.DOUBLE_PRECISION, nullable=False,
    )
    _southwest_latitude = sa.Column(
        'southwest_latitude', postgresql.DOUBLE_PRECISION, nullable=False,
    )
    _southwest_longitude = sa.Column(
        'southwest_longitude', postgresql.DOUBLE_PRECISION, nullable=False,
    )
    initial_zoom = sa.Column(sa.SmallInteger, nullable=False)

    # Relationships
    addresses = orm.relationship('Address', back_populates='city')

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Create a new city."""
        # Call SQLAlchemy's default `.__init__()` method.
        super().__init__(*args, **kwargs)

        # Take the "lower left" of the viewport as the origin
        # of a Cartesian coordinate system.
        lower_left = self.viewport['southwest']
        self._origin = utils.UTMCoordinate(
            lower_left['latitude'], lower_left['longitude'],
        )

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({name})>'.format(cls=self.__class__.__name__, name=self.name)

    @property
    def location(self) -> Dict[str, float]:
        """GPS location of the city's center.

        Example:
            {"latitude": 48.856614, "longitude": 2.3522219}
        """
        return {
            'latitude': self._center_latitude,
            'longitude': self._center_longitude,
        }

    @property
    def viewport(self) -> Dict[str, Dict[str, float]]:
        """Google Maps viewport of the city.

        Example:
            {
                'northeast': {'latitude': 48.9021449, 'longitude': 2.4699208},
                'southwest': {'latitude': 48.815573, 'longitude': 2.225193},
            }
        """  # noqa:RST203
        return {
            'northeast': {
                'latitude': self._northeast_latitude,
                'longitude': self._northeast_longitude,
            },
            'southwest': {
                'latitude': self._southwest_latitude,
                'longitude': self._southwest_longitude,
            },
        }

    @property
    def as_origin(self) -> utils.UTMCoordinate:
        """The lower left corner of the `.viewport` in UTM coordinates.

        This property serves as the `relative_to` argument to the
        `UTMConstructor` when representing an `Address` in the x-y plane.
        """
        return self._origin
