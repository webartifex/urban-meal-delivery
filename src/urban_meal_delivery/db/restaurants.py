"""Provide the ORM's `Restaurant` model."""

from __future__ import annotations

import folium
import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery import config
from urban_meal_delivery import db
from urban_meal_delivery.db import meta


class Restaurant(meta.Base):
    """A restaurant selling meals on the UDP.

    In the historic dataset, a `Restaurant` may have changed its `Address`
    throughout its life time. The ORM model only stores the current one,
    which in most cases is also the only one.
    """

    __tablename__ = 'restaurants'

    # Columns
    id = sa.Column(  # noqa:WPS125
        sa.SmallInteger, primary_key=True, autoincrement=False,
    )
    created_at = sa.Column(sa.DateTime, nullable=False)
    name = sa.Column(sa.Unicode(length=45), nullable=False)
    address_id = sa.Column(sa.Integer, nullable=False, index=True)
    estimated_prep_duration = sa.Column(sa.SmallInteger, nullable=False)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['address_id'], ['addresses.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 2400',
            name='realistic_estimated_prep_duration',
        ),
        # Needed by a `ForeignKeyConstraint` in `Order`.
        sa.UniqueConstraint('id', 'address_id'),
    )

    # Relationships
    address = orm.relationship('Address', back_populates='restaurants')
    orders = orm.relationship('Order', back_populates='restaurant')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({name})>'.format(cls=self.__class__.__name__, name=self.name)

    def clear_map(self) -> Restaurant:  # pragma: no cover
        """Shortcut to the `.address.city.clear_map()` method.

        Returns:
            self: enabling method chaining
        """  # noqa:D402,DAR203
        self.address.city.clear_map()
        return self

    @property  # pragma: no cover
    def map(self) -> folium.Map:  # noqa:WPS125
        """Shortcut to the `.address.city.map` object."""
        return self.address.city.map

    def draw(  # noqa:WPS231
        self, customers: bool = True, order_counts: bool = False,  # pragma: no cover
    ) -> folium.Map:
        """Draw the restaurant on the `.address.city.map`.

        By default, the restaurant's delivery locations are also shown.

        Args:
            customers: show the restaurant's delivery locations
            order_counts: show the number of orders at the delivery locations;
                only useful if `customers=True`

        Returns:
            `.address.city.map` for convenience in interactive usage
        """
        if customers:
            # Obtain all primary `Address`es in the city that
            # received at least one delivery from `self`.
            delivery_addresses = (  # noqa:ECE001
                db.session.query(db.Address)
                .filter(
                    db.Address.id.in_(
                        db.session.query(db.Address.primary_id)  # noqa:WPS221
                        .join(db.Order, db.Address.id == db.Order.delivery_address_id)
                        .filter(db.Order.restaurant_id == self.id)
                        .distinct()
                        .all(),
                    ),
                )
                .all()
            )

            for address in delivery_addresses:
                if order_counts:
                    n_orders = (  # noqa:ECE001
                        db.session.query(db.Order)
                        .join(db.Address, db.Order.delivery_address_id == db.Address.id)
                        .filter(db.Order.restaurant_id == self.id)
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

        self.address.draw(
            radius=20,
            color=config.RESTAURANT_COLOR,
            fill_color=config.RESTAURANT_COLOR,
            fill_opacity=0.3,
            tooltip=f'{self.name} (#{self.id}) | n_orders={len(self.orders)}',
        )

        return self.map
