"""Model for the relationship between two `Address` objects (= distance matrix)."""

from __future__ import annotations

import itertools
import json
from typing import List

import googlemaps as gm
import ordered_set
import sqlalchemy as sa
from geopy import distance as geo_distance
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery import config
from urban_meal_delivery import db
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

    @classmethod
    def from_addresses(
        cls, *addresses: db.Address, google_maps: bool = False,
    ) -> List[DistanceMatrix]:
        """Calculate pair-wise distances for `Address` objects.

        This is the main constructor method for the class.

        It handles the "sorting" of the `Address` objects by `.id`, which is
        the logic that enforces the symmetric graph behind the distances.

        Args:
            *addresses: to calculate the pair-wise distances for;
                must contain at least two `Address` objects
            google_maps: if `.bicylce_distance` and `.directions` should be
                populated with a query to the Google Maps Directions API;
                by default, only the `.air_distance` is calculated with `geopy`

        Returns:
            distances
        """
        distances = []

        # We consider all 2-tuples of `Address`es. The symmetric graph is ...
        for first, second in itertools.combinations(addresses, 2):
            # ... implicitly enforced by a precedence constraint for the `.id`s.
            first, second = (  # noqa:WPS211
                (first, second) if first.id < second.id else (second, first)
            )

            # If there is no `DistaneMatrix` object in the database ...
            distance = (  # noqa:ECE001
                db.session.query(db.DistanceMatrix)
                .filter(db.DistanceMatrix.first_address == first)
                .filter(db.DistanceMatrix.second_address == second)
                .first()
            )
            # ... create a new one.
            if distance is None:
                air_distance = geo_distance.great_circle(
                    first.location.lat_lng, second.location.lat_lng,
                )

                distance = cls(
                    first_address=first,
                    second_address=second,
                    air_distance=round(air_distance.meters),
                )

                db.session.add(distance)
                db.session.commit()

            distances.append(distance)

        if google_maps:
            for distance in distances:  # noqa:WPS440
                distance.sync_with_google_maps()

        return distances

    def sync_with_google_maps(self) -> None:
        """Fill in `.bicycle_distance` and `.directions` with Google Maps.

        `.directions` will not contain the coordinates of `.first_address` and
        `.second_address`.

        This uses the Google Maps Directions API.

        Further info:
            https://developers.google.com/maps/documentation/directions
        """
        # To save costs, we do not make an API call
        # if we already have data from Google Maps.
        if self.bicycle_distance is not None:
            return

        client = gm.Client(config.GOOGLE_MAPS_API_KEY)
        response = client.directions(
            origin=self.first_address.location.lat_lng,
            destination=self.second_address.location.lat_lng,
            mode='bicycling',
            alternatives=False,
        )
        # Without "alternatives" and "waypoints", the `response` contains
        # exactly one "route" that consists of exactly one "leg".
        # Source: https://developers.google.com/maps/documentation/directions/get-directions#Legs  # noqa:E501
        route = response[0]['legs'][0]

        self.bicycle_distance = route['distance']['value']  # noqa:WPS601
        self.bicycle_duration = route['duration']['value']  # noqa:WPS601

        # Each route consists of many "steps" that are instructions as to how to
        # get from A to B. As a step's "start_location" may equal the previous step's
        # "end_location", we use an `OrderedSet` to find the unique latitude-longitude
        # pairs that make up the path from `.first_address` to `.second_address`.
        steps = ordered_set.OrderedSet()
        for step in route['steps']:
            steps.add(  # noqa:WPS221
                (step['start_location']['lat'], step['start_location']['lng']),
            )
            steps.add(  # noqa:WPS221
                (step['end_location']['lat'], step['end_location']['lng']),
            )

        steps.discard(self.first_address.location.lat_lng)
        steps.discard(self.second_address.location.lat_lng)

        self.directions = json.dumps(list(steps))  # noqa:WPS601

        db.session.add(self)
        db.session.commit()

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