"""Provide the ORM's Address model."""

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext import hybrid

from urban_meal_delivery.db import meta


class Address(meta.Base):
    """An Address of a Customer or a Restaurant on the UDP."""

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
    _city_id = sa.Column('city_id', sa.SmallInteger, nullable=False, index=True)
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
        foreign_keys='[Order._pickup_address_id]',
    )

    orders_delivered = orm.relationship(
        'Order',
        back_populates='delivery_address',
        foreign_keys='[Order._delivery_address_id]',
    )

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({street} in {city})>'.format(
            cls=self.__class__.__name__, street=self.street, city=self.city_name,
        )

    @hybrid.hybrid_property
    def is_primary(self) -> bool:
        """If an Address object is the earliest one entered at its location.

        Street addresses may have been entered several times with different
        versions/spellings of the street name and/or different floors.

        `is_primary` indicates the first in a group of addresses.
        """
        return self.id == self._primary_id
