"""Provide the ORM's `Address` model."""

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext import hybrid

from urban_meal_delivery.db import meta
from urban_meal_delivery.db import utils


class Address(meta.Base):
    """An address of a `Customer` or a `Restaurant` on the UDP."""

    __tablename__ = 'addresses'

    # Columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)  # noqa:WPS125
    _primary_id = sa.Column('primary_id', sa.Integer, nullable=False, index=True)
    created_at = sa.Column(sa.DateTime, nullable=False)
    place_id = sa.Column(
        sa.Unicode(length=120), nullable=False, index=True,  # noqa:WPS432
    )
    latitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    longitude = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    city_id = sa.Column(sa.SmallInteger, nullable=False, index=True)
    city_name = sa.Column('city', sa.Unicode(length=25), nullable=False)  # noqa:WPS432
    zip_code = sa.Column(sa.Integer, nullable=False, index=True)
    street = sa.Column(sa.Unicode(length=80), nullable=False)  # noqa:WPS432
    floor = sa.Column(sa.SmallInteger)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['primary_id'], ['addresses.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['city_id'], ['cities.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            '-90 <= latitude AND latitude <= 90', name='latitude_between_90_degrees',
        ),
        sa.CheckConstraint(
            '-180 <= longitude AND longitude <= 180',
            name='longitude_between_180_degrees',
        ),
        # Needed by a `ForeignKeyConstraint` in `AddressPixelAssociation`.
        sa.UniqueConstraint('id', 'city_id'),
        sa.CheckConstraint(
            '30000 <= zip_code AND zip_code <= 99999', name='valid_zip_code',
        ),
        sa.CheckConstraint('0 <= floor AND floor <= 40', name='realistic_floor'),
    )

    # Relationships
    city = orm.relationship('City', back_populates='addresses')
    restaurant = orm.relationship('Restaurant', back_populates='address', uselist=False)
    orders_picked_up = orm.relationship(
        'Order',
        back_populates='pickup_address',
        foreign_keys='[Order.pickup_address_id]',
    )
    orders_delivered = orm.relationship(
        'Order',
        back_populates='delivery_address',
        foreign_keys='[Order.delivery_address_id]',
    )
    pixels = orm.relationship('AddressPixelAssociation', back_populates='address')

    # We do not implement a `.__init__()` method and leave that to SQLAlchemy.
    # Instead, we use `hasattr()` to check for uninitialized attributes.  grep:b1f68d24

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({street} in {city})>'.format(
            cls=self.__class__.__name__, street=self.street, city=self.city_name,
        )

    @hybrid.hybrid_property
    def is_primary(self) -> bool:
        """If an `Address` object is the earliest one entered at its location.

        Street addresses may have been entered several times with different
        versions/spellings of the street name and/or different floors.

        `.is_primary` indicates the first in a group of `Address` objects.
        """
        return self.id == self._primary_id

    @property
    def location(self) -> utils.Location:
        """The location of the address.

        The returned `Location` object relates to `.city.southwest`.

        See also the `.x` and `.y` properties that are shortcuts for
        `.location.x` and `.location.y`.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        if not hasattr(self, '_location'):  # noqa:WPS421  note:b1f68d24
            self._location = utils.Location(self.latitude, self.longitude)
            self._location.relate_to(self.city.southwest)
        return self._location

    @property
    def x(self) -> int:  # noqa=WPS111
        """The relative x-coordinate within the `.city` in meters.

        On the implied x-y plane, the `.city`'s southwest corner is the origin.

        Shortcut for `.location.x`.
        """
        return self.location.x

    @property
    def y(self) -> int:  # noqa=WPS111
        """The relative y-coordinate within the `.city` in meters.

        On the implied x-y plane, the `.city`'s southwest corner is the origin.

        Shortcut for `.location.y`.
        """
        return self.location.y
