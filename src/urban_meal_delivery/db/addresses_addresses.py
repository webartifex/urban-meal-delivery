"""Model for the relationship between two `Address` objects (= distance matrix)."""

import json
from typing import List

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery.db import meta
from urban_meal_delivery.db import utils


class DistanceMatrix(meta.Base):
    """Distance matrix between `Address` objects.

    Models the pairwise distances between two `Address` objects,
    including directions for a `Courier` to get from one `Address` to another.

    As the couriers are on bicycles, we model the distance matrix
    as a symmetric graph (i.e., same distance in both directions).

    Implements an association pattern between `Address` and `Address`.

    Further info:
        https://docs.sqlalchemy.org/en/stable/orm/basic_relationships.html#association-object  # noqa:E501
    """

    __tablename__ = 'addresses_addresses'

    # Columns
    first_address_id = sa.Column(sa.Integer, primary_key=True)
    second_address_id = sa.Column(sa.Integer, primary_key=True)
    city_id = sa.Column(sa.SmallInteger, nullable=False)
    # Distances are measured in meters.
    air_distance = sa.Column(sa.Integer, nullable=False)
    bicycle_distance = sa.Column(sa.Integer, nullable=True)
    # The duration is measured in seconds.
    bicycle_duration = sa.Column(sa.Integer, nullable=True)
    # An array of latitude-longitude pairs approximating a courier's way.
    directions = sa.Column(postgresql.JSON, nullable=True)

    # Constraints
    __table_args__ = (
        # The two `Address` objects must be in the same `.city`.
        sa.ForeignKeyConstraint(
            ['first_address_id', 'city_id'],
            ['addresses.id', 'addresses.city_id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['second_address_id', 'city_id'],
            ['addresses.id', 'addresses.city_id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        # Each `Address`-`Address` pair only has one distance.
        sa.UniqueConstraint('first_address_id', 'second_address_id'),
        sa.CheckConstraint(
            'first_address_id < second_address_id',
            name='distances_are_symmetric_for_bicycles',
        ),
        sa.CheckConstraint(
            '0 <= air_distance AND air_distance < 20000', name='realistic_air_distance',
        ),
        sa.CheckConstraint(
            'bicycle_distance < 25000',  # `.bicycle_distance` may not be negatative
            name='realistic_bicycle_distance',  # due to the constraint below.
        ),
        sa.CheckConstraint(
            'air_distance <= bicycle_distance', name='air_distance_is_shortest',
        ),
        sa.CheckConstraint(
            '0 <= bicycle_duration AND bicycle_duration <= 3600',
            name='realistic_bicycle_travel_time',
        ),
    )

    # Relationships
    first_address = orm.relationship(
        'Address',
        back_populates='_distances1',
        foreign_keys='[DistanceMatrix.first_address_id, DistanceMatrix.city_id]',
    )
    second_address = orm.relationship(
        'Address',
        back_populates='_distances2',
        foreign_keys='[DistanceMatrix.second_address_id, DistanceMatrix.city_id]',
    )

    # We do not implement a `.__init__()` method and leave that to SQLAlchemy.
    # Instead, we use `hasattr()` to check for uninitialized attributes.  grep:86ffc14e

    @property
    def path(self) -> List[utils.Location]:
        """The couriers' path from `.first_address` to `.second_address`.

        The returned `Location`s all relates to `.first_address.city.southwest`.

        Implementation detail: This property is cached as none of the
        underlying attributes (i.e., `.directions`) are to be changed.
        """
        if not hasattr(self, '_path'):  # noqa:WPS421  note:86ffc14e
            inner_points = [
                utils.Location(point[0], point[1])
                for point in json.loads(self.directions)
            ]
            for point in inner_points:
                point.relate_to(self.first_address.city.southwest)

            self._path = inner_points

        return self._path