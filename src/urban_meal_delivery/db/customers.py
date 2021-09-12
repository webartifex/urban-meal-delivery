"""Provide the ORM's `Customer` model."""

from __future__ import annotations

import folium
import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery import config
from urban_meal_delivery import db
from urban_meal_delivery.db import meta


class Customer(meta.Base):
    """A customer of the UDP."""

    __tablename__ = 'customers'

    # Columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)  # noqa:WPS125

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}(#{customer_id})>'.format(
            cls=self.__class__.__name__, customer_id=self.id,
        )

    # Relationships
    orders = orm.relationship('Order', back_populates='customer')

    def clear_map(self) -> Customer:  # pragma: no cover
        """Shortcut to the `...city.clear_map()` method.

        Returns:
            self: enabling method chaining
        """  # noqa:D402,DAR203
        self.orders[0].pickup_address.city.clear_map()  # noqa:WPS219
        return self

    @property  # pragma: no cover
    def map(self) -> folium.Map:  # noqa:WPS125
        """Shortcut to the `...city.map` object."""
        return self.orders[0].pickup_address.city.map  # noqa:WPS219

    def draw(  # noqa:C901,WPS210,WPS231
        self, restaurants: bool = True, order_counts: bool = False,  # pragma: no cover
    ) -> folium.Map:
        """Draw all the customer's delivery addresses on the `...city.map`.

        By default, the pickup locations (= restaurants) are also shown.

        Args:
            restaurants: show the pickup locations
            order_counts: show both the number of pickups at the restaurants
                and the number of deliveries at the customer's delivery addresses;
                the former is only shown if `restaurants=True`

        Returns:
            `...city.map` for convenience in interactive usage
        """
        # Note: a `Customer` may have more than one delivery `Address`es.
        # That is not true for `Restaurant`s after the data cleaning.

        # Obtain all primary `Address`es where
        # at least one delivery was made to `self`.
        delivery_addresses = (
            db.session.query(db.Address)
            .filter(
                db.Address.id.in_(
                    row.primary_id
                    for row in (
                        db.session.query(db.Address.primary_id)  # noqa:WPS221
                        .join(db.Order, db.Address.id == db.Order.delivery_address_id)
                        .filter(db.Order.customer_id == self.id)
                        .distinct()
                        .all()
                    )
                ),
            )
            .all()
        )

        for address in delivery_addresses:
            if order_counts:
                n_orders = (
                    db.session.query(db.Order)
                    .join(db.Address, db.Order.delivery_address_id == db.Address.id)
                    .filter(db.Order.customer_id == self.id)
                    .filter(db.Address.primary_id == address.id)
                    .count()
                )
                if n_orders >= 25:
                    radius = 20  # noqa:WPS220
                elif n_orders >= 10:
                    radius = 15  # noqa:WPS220
                elif n_orders >= 5:
                    radius = 10  # noqa:WPS220
                elif n_orders > 1:
                    radius = 5  # noqa:WPS220
                else:
                    radius = 1  # noqa:WPS220

                address.draw(
                    radius=radius,
                    color=config.CUSTOMER_COLOR,
                    fill_color=config.CUSTOMER_COLOR,
                    fill_opacity=0.3,
                    tooltip=f'n_orders={n_orders}',
                )

            else:
                address.draw(
                    radius=1, color=config.CUSTOMER_COLOR,
                )

        if restaurants:
            pickup_addresses = (
                db.session.query(db.Address)
                .filter(
                    db.Address.id.in_(
                        db.session.query(db.Address.primary_id)  # noqa:WPS221
                        .join(db.Order, db.Address.id == db.Order.pickup_address_id)
                        .filter(db.Order.customer_id == self.id)
                        .distinct()
                        .all(),
                    ),
                )
                .all()
            )

            for address in pickup_addresses:  # noqa:WPS440
                # Show the restaurant's name if there is only one.
                # Otherwise, list all the restaurants' ID's.
                # We cannot show the `Order.restaurant.name` due to the aggregation.
                restaurants = (
                    db.session.query(db.Restaurant)
                    .join(db.Address, db.Restaurant.address_id == db.Address.id)
                    .filter(db.Address.primary_id == address.id)  # noqa:WPS441
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
                    n_orders = (
                        db.session.query(db.Order)
                        .join(db.Address, db.Order.pickup_address_id == db.Address.id)
                        .filter(db.Order.customer_id == self.id)
                        .filter(db.Address.primary_id == address.id)  # noqa:WPS441
                        .count()
                    )
                    if n_orders >= 25:
                        radius = 20  # noqa:WPS220
                    elif n_orders >= 10:
                        radius = 15  # noqa:WPS220
                    elif n_orders >= 5:
                        radius = 10  # noqa:WPS220
                    elif n_orders > 1:
                        radius = 5  # noqa:WPS220
                    else:
                        radius = 1  # noqa:WPS220

                    tooltip += f' | n_orders={n_orders}'  # noqa:WPS336

                    address.draw(  # noqa:WPS441
                        radius=radius,
                        color=config.RESTAURANT_COLOR,
                        fill_color=config.RESTAURANT_COLOR,
                        fill_opacity=0.3,
                        tooltip=tooltip,
                    )

                else:
                    address.draw(  # noqa:WPS441
                        radius=1, color=config.RESTAURANT_COLOR, tooltip=tooltip,
                    )

        return self.map
