"""Provide the ORM's `Pixel` model."""

from __future__ import annotations

from typing import List

import folium
import sqlalchemy as sa
import utm
from sqlalchemy import orm

from urban_meal_delivery import config
from urban_meal_delivery import db
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
        return '<{cls}: ({x}|{y})>'.format(
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

    @property
    def restaurants(self) -> List[db.Restaurant]:  # pragma: no cover
        """Obtain all `Restaurant`s in `self`."""
        if not hasattr(self, '_restaurants'):  # noqa:WPS421  note:d334120e
            self._restaurants = (  # noqa:ECE001
                db.session.query(db.Restaurant)
                .join(
                    db.AddressPixelAssociation,
                    db.Restaurant.address_id == db.AddressPixelAssociation.address_id,
                )
                .filter(db.AddressPixelAssociation.pixel_id == self.id)
                .all()
            )

        return self._restaurants

    def clear_map(self) -> Pixel:  # pragma: no cover
        """Shortcut to the `.city.clear_map()` method.

        Returns:
            self: enabling method chaining
        """  # noqa:D402,DAR203
        self.grid.city.clear_map()
        return self

    @property  # pragma: no cover
    def map(self) -> folium.Map:  # noqa:WPS125
        """Shortcut to the `.city.map` object."""
        return self.grid.city.map

    def draw(  # noqa:C901,WPS210,WPS231
        self, restaurants: bool = True, order_counts: bool = False,  # pragma: no cover
    ) -> folium.Map:
        """Draw the pixel on the `.grid.city.map`.

        Args:
            restaurants: include the restaurants
            order_counts: show the number of orders at a restaurant

        Returns:
            `.grid.city.map` for convenience in interactive usage
        """
        bounds = (
            (self.southwest.latitude, self.southwest.longitude),
            (self.northeast.latitude, self.northeast.longitude),
        )
        info_text = f'Pixel({self.n_x}|{self.n_y})'

        # Make the `Pixel`s look like a checkerboard.
        if (self.n_x + self.n_y) % 2:
            color = '#808000'
        else:
            color = '#ff8c00'

        marker = folium.Rectangle(
            bounds=bounds,
            color='gray',
            opacity=0.2,
            weight=5,
            fill_color=color,
            fill_opacity=0.2,
            popup=info_text,
            tooltip=info_text,
        )
        marker.add_to(self.grid.city.map)

        if restaurants:
            # Obtain all primary `Address`es in the city that host `Restaurant`s
            # and are in the `self` `Pixel`.
            addresses = (  # noqa:ECE001
                db.session.query(db.Address)
                .filter(
                    db.Address.id.in_(
                        (
                            db.session.query(db.Address.primary_id)
                            .join(
                                db.Restaurant,
                                db.Address.id == db.Restaurant.address_id,
                            )
                            .join(
                                db.AddressPixelAssociation,
                                db.Address.id == db.AddressPixelAssociation.address_id,
                            )
                            .filter(db.AddressPixelAssociation.pixel_id == self.id)
                        )
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
                if len(restaurants) == 1:  # type:ignore
                    tooltip = (
                        f'{restaurants[0].name} (#{restaurants[0].id})'  # type:ignore
                    )
                else:
                    tooltip = 'Restaurants ' + ', '.join(  # noqa:WPS336
                        f'#{restaurant.id}' for restaurant in restaurants  # type:ignore
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
