"""Provide the ORM's `City` model."""

from __future__ import annotations

import functools

import folium
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery import config
from urban_meal_delivery import db
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

    # We do not implement a `.__init__()` method and use SQLAlchemy's default.
    # The uninitialized attribute `._map` is computed on the fly.  note:d334120ei

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({name})>'.format(cls=self.__class__.__name__, name=self.name)

    @functools.cached_property
    def center(self) -> utils.Location:
        """Location of the city's center.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        return utils.Location(self.center_latitude, self.center_longitude)

    @functools.cached_property
    def northeast(self) -> utils.Location:
        """The city's northeast corner of the Google Maps viewport.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        return utils.Location(self.northeast_latitude, self.northeast_longitude)

    @functools.cached_property
    def southwest(self) -> utils.Location:
        """The city's southwest corner of the Google Maps viewport.

        Implementation detail: This property is cached as none of the
        underlying attributes to calculate the value are to be changed.
        """
        return utils.Location(self.southwest_latitude, self.southwest_longitude)

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

    def clear_map(self) -> City:  # pragma: no cover
        """Create a new `folium.Map` object aligned with the city's viewport.

        The map is available via the `.map` property. Note that it is mutable
        and changed from various locations in the code base.

        Returns:
            self: enabling method chaining
        """  # noqa:DAR203  note:d334120e
        self._map = folium.Map(
            location=[self.center_latitude, self.center_longitude],
            zoom_start=self.initial_zoom,
        )

        return self

    @property  # pragma: no cover
    def map(self) -> folium.Map:  # noqa:WPS125
        """A `folium.Map` object aligned with the city's viewport.

        See docstring for `.clear_map()` for further info.
        """
        if not hasattr(self, '_map'):  # noqa:WPS421  note:d334120e
            self.clear_map()

        return self._map

    def draw_restaurants(  # noqa:WPS231
        self, order_counts: bool = False,  # pragma: no cover
    ) -> folium.Map:
        """Draw all restaurants on the`.map`.

        Args:
            order_counts: show the number of orders

        Returns:
            `.map` for convenience in interactive usage
        """
        # Obtain all primary `Address`es in the city that host `Restaurant`s.
        addresses = (  # noqa:ECE001
            db.session.query(db.Address)
            .filter(
                db.Address.id.in_(
                    db.session.query(db.Address.primary_id)  # noqa:WPS221
                    .join(db.Restaurant, db.Address.id == db.Restaurant.address_id)
                    .filter(db.Address.city == self)
                    .distinct()
                    .all(),
                ),
            )
            .all()
        )

        for address in addresses:
            # Show the restaurant's name if there is only one.
            # Otherwise, list all the restaurants' ID's.
            restaurants = (  # noqa:ECE001
                db.session.query(db.Restaurant)
                .join(db.Address, db.Restaurant.address_id == db.Address.id)
                .filter(db.Address.primary_id == address.id)
                .all()
            )
            if len(restaurants) == 1:
                tooltip = f'{restaurants[0].name} (#{restaurants[0].id})'  # noqa:WPS221
            else:
                tooltip = 'Restaurants ' + ', '.join(  # noqa:WPS336
                    f'#{restaurant.id}' for restaurant in restaurants
                )

            if order_counts:
                # Calculate the number of orders for ALL restaurants ...
                n_orders = (  # noqa:ECE001
                    db.session.query(db.Order.id)
                    .join(db.Address, db.Order.pickup_address_id == db.Address.id)
                    .filter(db.Address.primary_id == address.id)
                    .count()
                )
                # ... and adjust the size of the red dot on the `.map`.
                if n_orders >= 1000:
                    radius = 20  # noqa:WPS220
                elif n_orders >= 500:
                    radius = 15  # noqa:WPS220
                elif n_orders >= 100:
                    radius = 10  # noqa:WPS220
                elif n_orders >= 10:
                    radius = 5  # noqa:WPS220
                else:
                    radius = 1  # noqa:WPS220

                tooltip += f' | n_orders={n_orders}'  # noqa:WPS336

                address.draw(
                    radius=radius,
                    color=config.RESTAURANT_COLOR,
                    fill_color=config.RESTAURANT_COLOR,
                    fill_opacity=0.3,
                    tooltip=tooltip,
                )

            else:
                address.draw(
                    radius=1, color=config.RESTAURANT_COLOR, tooltip=tooltip,
                )

        return self.map

    def draw_zip_codes(self) -> folium.Map:  # pragma: no cover
        """Draw all addresses on the `.map`, colorized by their `.zip_code`.

        This does not make a distinction between restaurant and customer addresses.
        Also, due to the high memory usage, the number of orders is not calculated.

        Returns:
            `.map` for convenience in interactive usage
        """
        # First, create a color map with distinct colors for each zip code.
        all_zip_codes = sorted(
            row[0]
            for row in db.session.execute(
                sa.text(
                    f"""  -- # noqa:S608
                    SELECT DISTINCT
                        {config.CLEAN_SCHEMA}.addresses.zip_code
                    FROM
                        {config.CLEAN_SCHEMA}.addresses AS addresses
                    WHERE
                        {config.CLEAN_SCHEMA}.addresses.city_id = {self.id};
                    """,
                ),
            )
        )
        cmap = utils.make_random_cmap(len(all_zip_codes), bright=False)
        colors = {
            code: utils.rgb_to_hex(*cmap(index))
            for index, code in enumerate(all_zip_codes)
        }

        # Second, draw every address on the `.map.
        for address in self.addresses:
            # Non-primary addresses are covered by primary ones anyway.
            if not address.is_primary:
                continue

            marker = folium.Circle(  # noqa:WPS317
                (address.latitude, address.longitude),
                color=colors[address.zip_code],
                radius=1,
            )
            marker.add_to(self.map)

        return self.map
