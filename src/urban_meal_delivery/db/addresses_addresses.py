"""Model for the `Path` relationship between two `Address` objects."""

from __future__ import annotations

import functools
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


class Path(meta.Base):
    """Path between two `Address` objects.

    Models the path between two `Address` objects, including directions
    for a `Courier` to get from one `Address` to another.

    As the couriers are on bicycles, we model the paths as
    a symmetric graph (i.e., same distance in both directions).

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
    _directions = sa.Column('directions', postgresql.JSON, nullable=True)

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
            'bicycle_distance < 25000',  # `.bicycle_distance` may not be negative
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
        'Address', foreign_keys='[Path.first_address_id, Path.city_id]',
    )
    second_address = orm.relationship(
        'Address',
        foreign_keys='[Path.second_address_id, Path.city_id]',
        overlaps='first_address',
    )

    @classmethod
    def from_addresses(
        cls, *addresses: db.Address, google_maps: bool = False,
    ) -> List[Path]:
        """Calculate pair-wise paths for `Address` objects.

        This is the main constructor method for the class.

        It handles the "sorting" of the `Address` objects by `.id`, which is
        the logic that enforces the symmetric graph behind the paths.

        Args:
            *addresses: to calculate the pair-wise paths for;
                must contain at least two `Address` objects
            google_maps: if `.bicycle_distance` and `._directions` should be
                populated with a query to the Google Maps Directions API;
                by default, only the `.air_distance` is calculated with `geopy`

        Returns:
            paths
        """
        paths = []

        # We consider all 2-tuples of `Address`es. The symmetric graph is ...
        for first, second in itertools.combinations(addresses, 2):
            # ... implicitly enforced by a precedence constraint for the `.id`s.
            first, second = (  # noqa:WPS211
                (first, second) if first.id < second.id else (second, first)
            )

            # If there is no `Path` object in the database ...
            path = (
                db.session.query(db.Path)
                .filter(db.Path.first_address == first)
                .filter(db.Path.second_address == second)
                .first()
            )
            # ... create a new one.
            if path is None:
                air_distance = geo_distance.great_circle(
                    first.location.lat_lng, second.location.lat_lng,
                )

                path = cls(
                    first_address=first,
                    second_address=second,
                    air_distance=round(air_distance.meters),
                )

                db.session.add(path)
                db.session.commit()

            paths.append(path)

        if google_maps:
            for path in paths:  # noqa:WPS440
                path.sync_with_google_maps()

        return paths

    @classmethod
    def from_order(cls, order: db.Order, google_maps: bool = False) -> Path:
        """Calculate the path for an `Order` object.

        The path goes from the `Order.pickup_address` to the `Order.delivery_address`.

        Args:
            order: to calculate the path for
            google_maps: if `.bicycle_distance` and `._directions` should be
                populated with a query to the Google Maps Directions API;
                by default, only the `.air_distance` is calculated with `geopy`

        Returns:
            path
        """
        return cls.from_addresses(
            order.pickup_address, order.delivery_address, google_maps=google_maps,
        )[0]

    def sync_with_google_maps(self) -> None:
        """Fill in `.bicycle_distance` and `._directions` with Google Maps.

        `._directions` will NOT contain the coordinates
        of `.first_address` and `.second_address`.

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

        self._directions = json.dumps(list(steps))  # noqa:WPS601

        db.session.add(self)
        db.session.commit()

    @functools.cached_property
    def waypoints(self) -> List[utils.Location]:
        """The couriers' route from `.first_address` to `.second_address`.

        The returned `Location`s all relate to `.first_address.city.southwest`.

        Implementation detail: This property is cached as none of the
        underlying attributes (i.e., `._directions`) are to be changed.
        """
        points = [utils.Location(*point) for point in json.loads(self._directions)]
        for point in points:
            point.relate_to(self.first_address.city.southwest)

        return points
