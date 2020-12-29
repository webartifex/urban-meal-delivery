"""Provide the ORM's `Courier` model."""

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery.db import meta


class Courier(meta.Base):
    """A courier working for the UDP."""

    __tablename__ = 'couriers'

    # Columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)  # noqa:WPS125
    created_at = sa.Column(sa.DateTime, nullable=False)
    vehicle = sa.Column(sa.Unicode(length=10), nullable=False)
    historic_speed = sa.Column('speed', postgresql.DOUBLE_PRECISION, nullable=False)
    capacity = sa.Column(sa.SmallInteger, nullable=False)
    pay_per_hour = sa.Column(sa.SmallInteger, nullable=False)
    pay_per_order = sa.Column(sa.SmallInteger, nullable=False)

    # Constraints
    __table_args__ = (
        sa.CheckConstraint(
            "vehicle IN ('bicycle', 'motorcycle')", name='available_vehicle_types',
        ),
        sa.CheckConstraint('0 <= speed AND speed <= 30', name='realistic_speed'),
        sa.CheckConstraint(
            '0 <= capacity AND capacity <= 200', name='capacity_under_200_liters',
        ),
        sa.CheckConstraint(
            '0 <= pay_per_hour AND pay_per_hour <= 1500', name='realistic_pay_per_hour',
        ),
        sa.CheckConstraint(
            '0 <= pay_per_order AND pay_per_order <= 650',
            name='realistic_pay_per_order',
        ),
    )

    # Relationships
    orders = orm.relationship('Order', back_populates='courier')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}(#{courier_id})>'.format(
            cls=self.__class__.__name__, courier_id=self.id,
        )
