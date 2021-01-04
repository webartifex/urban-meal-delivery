"""Provide the ORM's `City` model."""

from typing import Dict

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
    grids = orm.relationship('Grid', back_populates='city')

    # We do not implement a `.__init__()` method and leave that to SQLAlchemy.
    # Instead, we use `hasattr()` to check for uninitialized attributes.
    # grep:d334120e  pylint:disable=attribute-defined-outside-init

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
            self._center = utils.Location(
                self._center_latitude, self._center_longitude,
            )
        return self._center

    @property
    def viewport(self) -> Dict[str, utils.Location]:
        """Google Maps viewport of the city.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_viewport'):  # noqa:WPS421  note:d334120e
            self._viewport = {
                'northeast': utils.Location(
                    self._northeast_latitude, self._northeast_longitude,
                ),
                'southwest': utils.Location(
                    self._southwest_latitude, self._southwest_longitude,
                ),
            }

        return self._viewport

    @property
    def as_xy_origin(self) -> utils.Location:
        """The southwest corner of the `.viewport`.

        This property serves, for example, as the `other` argument to the
        `Location.relate_to()` method when representing an `Address`
        in the x-y plane.
        """
        return self.viewport['southwest']
