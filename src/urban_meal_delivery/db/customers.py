"""Provide the ORM's Customer model."""

import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery.db import meta


class Customer(meta.Base):
    """A Customer of the UDP."""

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
