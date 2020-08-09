"""Provide the ORM's Order model."""

import datetime

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery.db import meta


class Order(meta.Base):  # noqa:WPS214
    """An Order by a Customer of the UDP."""

    __tablename__ = 'orders'

    # Generic columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)  # noqa:WPS125
    _delivery_id = sa.Column('delivery_id', sa.Integer, index=True, unique=True)
    _customer_id = sa.Column('customer_id', sa.Integer, nullable=False, index=True)
    placed_at = sa.Column(sa.DateTime, nullable=False, index=True)
    ad_hoc = sa.Column(sa.Boolean, nullable=False)
    scheduled_delivery_at = sa.Column(sa.DateTime, index=True)
    scheduled_delivery_at_corrected = sa.Column(sa.Boolean, index=True)
    first_estimated_delivery_at = sa.Column(sa.DateTime)
    cancelled = sa.Column(sa.Boolean, nullable=False, index=True)
    cancelled_at = sa.Column(sa.DateTime)
    cancelled_at_corrected = sa.Column(sa.Boolean, index=True)

    # Price-related columns
    sub_total = sa.Column(sa.Integer, nullable=False)
    delivery_fee = sa.Column(sa.SmallInteger, nullable=False)
    total = sa.Column(sa.Integer, nullable=False)

    # Restaurant-related columns
    _restaurant_id = sa.Column(
        'restaurant_id', sa.SmallInteger, nullable=False, index=True,
    )
    restaurant_notified_at = sa.Column(sa.DateTime)
    restaurant_notified_at_corrected = sa.Column(sa.Boolean, index=True)
    restaurant_confirmed_at = sa.Column(sa.DateTime)
    restaurant_confirmed_at_corrected = sa.Column(sa.Boolean, index=True)
    estimated_prep_duration = sa.Column(sa.Integer, index=True)
    estimated_prep_duration_corrected = sa.Column(sa.Boolean, index=True)
    estimated_prep_buffer = sa.Column(sa.Integer, nullable=False, index=True)

    # Dispatch-related columns
    _courier_id = sa.Column('courier_id', sa.Integer, index=True)
    dispatch_at = sa.Column(sa.DateTime)
    dispatch_at_corrected = sa.Column(sa.Boolean, index=True)
    courier_notified_at = sa.Column(sa.DateTime)
    courier_notified_at_corrected = sa.Column(sa.Boolean, index=True)
    courier_accepted_at = sa.Column(sa.DateTime)
    courier_accepted_at_corrected = sa.Column(sa.Boolean, index=True)
    utilization = sa.Column(sa.SmallInteger, nullable=False)

    # Pickup-related columns
    _pickup_address_id = sa.Column(
        'pickup_address_id', sa.Integer, nullable=False, index=True,
    )
    reached_pickup_at = sa.Column(sa.DateTime)
    pickup_at = sa.Column(sa.DateTime)
    pickup_at_corrected = sa.Column(sa.Boolean, index=True)
    pickup_not_confirmed = sa.Column(sa.Boolean)
    left_pickup_at = sa.Column(sa.DateTime)
    left_pickup_at_corrected = sa.Column(sa.Boolean, index=True)

    # Delivery-related columns
    _delivery_address_id = sa.Column(
        'delivery_address_id', sa.Integer, nullable=False, index=True,
    )
    reached_delivery_at = sa.Column(sa.DateTime)
    delivery_at = sa.Column(sa.DateTime)
    delivery_at_corrected = sa.Column(sa.Boolean, index=True)
    delivery_not_confirmed = sa.Column(sa.Boolean)
    _courier_waited_at_delivery = sa.Column('courier_waited_at_delivery', sa.Boolean)

    # Statistical columns
    logged_delivery_distance = sa.Column(sa.SmallInteger, nullable=True)
    logged_avg_speed = sa.Column(postgresql.DOUBLE_PRECISION, nullable=True)
    logged_avg_speed_distance = sa.Column(sa.SmallInteger, nullable=True)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['customer_id'], ['customers.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['restaurant_id'],
            ['restaurants.id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['courier_id'], ['couriers.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['pickup_address_id'],
            ['addresses.id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['delivery_address_id'],
            ['addresses.id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            """
                (ad_hoc IS TRUE AND scheduled_delivery_at IS NULL)
                OR
                (ad_hoc IS FALSE AND scheduled_delivery_at IS NOT NULL)
            """,
            name='either_ad_hoc_or_scheduled_order',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    ad_hoc IS TRUE
                    AND (
                        EXTRACT(HOUR FROM placed_at) < 11
                        OR
                        EXTRACT(HOUR FROM placed_at) > 22
                    )
                )
            """,
            name='ad_hoc_orders_within_business_hours',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    ad_hoc IS FALSE
                    AND (
                        (
                            EXTRACT(HOUR FROM scheduled_delivery_at) <= 11
                            AND
                            NOT (
                                EXTRACT(HOUR FROM scheduled_delivery_at) = 11
                                AND
                                EXTRACT(MINUTE FROM scheduled_delivery_at) = 45
                            )
                        )
                        OR
                        EXTRACT(HOUR FROM scheduled_delivery_at) > 22
                    )
                )
            """,
            name='scheduled_orders_within_business_hours',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    EXTRACT(EPOCH FROM scheduled_delivery_at - placed_at) < 1800
                )
            """,
            name='scheduled_orders_not_within_30_minutes',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    cancelled IS FALSE
                    AND
                    cancelled_at IS NOT NULL
                )
            """,
            name='only_cancelled_orders_may_have_cancelled_at',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    cancelled IS TRUE
                    AND
                    delivery_at IS NOT NULL
                )
            """,
            name='cancelled_orders_must_not_be_delivered',
        ),
        sa.CheckConstraint(
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 2700',
            name='estimated_prep_duration_between_0_and_2700',
        ),
        sa.CheckConstraint(
            'estimated_prep_duration % 60 = 0',
            name='estimated_prep_duration_must_be_whole_minutes',
        ),
        sa.CheckConstraint(
            '0 <= estimated_prep_buffer AND estimated_prep_buffer <= 900',
            name='estimated_prep_buffer_between_0_and_900',
        ),
        sa.CheckConstraint(
            'estimated_prep_buffer % 60 = 0',
            name='estimated_prep_buffer_must_be_whole_minutes',
        ),
        sa.CheckConstraint(
            '0 <= utilization AND utilization <= 100',
            name='utilization_between_0_and_100',
        ),
        *(
            sa.CheckConstraint(
                f"""
                    ({column} IS NULL AND {column}_corrected IS NULL)
                    OR
                    ({column} IS NULL AND {column}_corrected IS TRUE)
                    OR
                    ({column} IS NOT NULL AND {column}_corrected IS NOT NULL)
                """,
                name=f'corrections_only_for_set_value_{index}',
            )
            for index, column in enumerate(
                (
                    'scheduled_delivery_at',
                    'cancelled_at',
                    'restaurant_notified_at',
                    'restaurant_confirmed_at',
                    'estimated_prep_duration',
                    'dispatch_at',
                    'courier_notified_at',
                    'courier_accepted_at',
                    'pickup_at',
                    'left_pickup_at',
                    'delivery_at',
                ),
            )
        ),
        *(
            sa.CheckConstraint(
                f"""
                    ({event}_at IS NULL AND {event}_not_confirmed IS NULL)
                    OR
                    ({event}_at IS NOT NULL AND {event}_not_confirmed IS NOT NULL)
                """,
                name=f'{event}_not_confirmed_only_if_{event}',
            )
            for event in ('pickup', 'delivery')
        ),
        sa.CheckConstraint(
            """
               (delivery_at IS NULL AND courier_waited_at_delivery IS NULL)
               OR
               (delivery_at IS NOT NULL AND courier_waited_at_delivery IS NOT NULL)
            """,
            name='courier_waited_at_delivery_only_if_delivery',
        ),
        *(
            sa.CheckConstraint(
                constraint, name='ordered_timestamps_{index}'.format(index=index),
            )
            for index, constraint in enumerate(
                (
                    'placed_at < scheduled_delivery_at',
                    'placed_at < first_estimated_delivery_at',
                    'placed_at < cancelled_at',
                    'placed_at < restaurant_notified_at',
                    'placed_at < restaurant_confirmed_at',
                    'placed_at < dispatch_at',
                    'placed_at < courier_notified_at',
                    'placed_at < courier_accepted_at',
                    'placed_at < reached_pickup_at',
                    'placed_at < left_pickup_at',
                    'placed_at < reached_delivery_at',
                    'placed_at < delivery_at',
                    'cancelled_at > restaurant_notified_at',
                    'cancelled_at > restaurant_confirmed_at',
                    'cancelled_at > dispatch_at',
                    'cancelled_at > courier_notified_at',
                    'cancelled_at > courier_accepted_at',
                    'cancelled_at > reached_pickup_at',
                    'cancelled_at > pickup_at',
                    'cancelled_at > left_pickup_at',
                    'cancelled_at > reached_delivery_at',
                    'cancelled_at > delivery_at',
                    'restaurant_notified_at < restaurant_confirmed_at',
                    'restaurant_notified_at < pickup_at',
                    'restaurant_confirmed_at < pickup_at',
                    'dispatch_at < courier_notified_at',
                    'dispatch_at < courier_accepted_at',
                    'dispatch_at < reached_pickup_at',
                    'dispatch_at < pickup_at',
                    'dispatch_at < left_pickup_at',
                    'dispatch_at < reached_delivery_at',
                    'dispatch_at < delivery_at',
                    'courier_notified_at < courier_accepted_at',
                    'courier_notified_at < reached_pickup_at',
                    'courier_notified_at < pickup_at',
                    'courier_notified_at < left_pickup_at',
                    'courier_notified_at < reached_delivery_at',
                    'courier_notified_at < delivery_at',
                    'courier_accepted_at < reached_pickup_at',
                    'courier_accepted_at < pickup_at',
                    'courier_accepted_at < left_pickup_at',
                    'courier_accepted_at < reached_delivery_at',
                    'courier_accepted_at < delivery_at',
                    'reached_pickup_at < pickup_at',
                    'reached_pickup_at < left_pickup_at',
                    'reached_pickup_at < reached_delivery_at',
                    'reached_pickup_at < delivery_at',
                    'pickup_at < left_pickup_at',
                    'pickup_at < reached_delivery_at',
                    'pickup_at < delivery_at',
                    'left_pickup_at < reached_delivery_at',
                    'left_pickup_at < delivery_at',
                    'reached_delivery_at < delivery_at',
                ),
            )
        ),
    )

    # Relationships
    customer = orm.relationship('Customer', back_populates='orders')
    restaurant = orm.relationship('Restaurant', back_populates='orders')
    courier = orm.relationship('Courier', back_populates='orders')
    pickup_address = orm.relationship(
        'Address',
        back_populates='orders_picked_up',
        foreign_keys='[Order._pickup_address_id]',
    )
    delivery_address = orm.relationship(
        'Address',
        back_populates='orders_delivered',
        foreign_keys='[Order._delivery_address_id]',
    )

    # Convenience properties

    @property
    def scheduled(self) -> bool:
        """Inverse of Order.ad_hoc."""
        return not self.ad_hoc

    @property
    def completed(self) -> bool:
        """Inverse of Order.cancelled."""
        return not self.cancelled

    @property
    def corrected(self) -> bool:
        """If any timestamp was corrected as compared to the original data."""
        return (
            self.scheduled_delivery_at_corrected  # noqa:WPS222 => too much logic
            or self.cancelled_at_corrected
            or self.restaurant_notified_at_corrected
            or self.restaurant_confirmed_at_corrected
            or self.dispatch_at_corrected
            or self.courier_notified_at_corrected
            or self.courier_accepted_at_corrected
            or self.pickup_at_corrected
            or self.left_pickup_at_corrected
            or self.delivery_at_corrected
        )

    # Timing-related properties

    @property
    def time_to_accept(self) -> datetime.timedelta:
        """Time until a courier accepted an order.

        This adds the time it took the UDP to notify a courier.
        """
        if not self.dispatch_at:
            raise RuntimeError('dispatch_at is not set')
        if not self.courier_accepted_at:
            raise RuntimeError('courier_accepted_at is not set')
        return self.courier_accepted_at - self.dispatch_at

    @property
    def time_to_react(self) -> datetime.timedelta:
        """Time a courier took to accept an order.

        This time is a subset of Order.time_to_accept.
        """
        if not self.courier_notified_at:
            raise RuntimeError('courier_notified_at is not set')
        if not self.courier_accepted_at:
            raise RuntimeError('courier_accepted_at is not set')
        return self.courier_accepted_at - self.courier_notified_at

    @property
    def time_to_pickup(self) -> datetime.timedelta:
        """Time from a courier's acceptance to arrival at the pickup location."""
        if not self.courier_accepted_at:
            raise RuntimeError('courier_accepted_at is not set')
        if not self.reached_pickup_at:
            raise RuntimeError('reached_pickup_at is not set')
        return self.reached_pickup_at - self.courier_accepted_at

    @property
    def time_at_pickup(self) -> datetime.timedelta:
        """Time a courier stayed at the pickup location."""
        if not self.reached_pickup_at:
            raise RuntimeError('reached_pickup_at is not set')
        if not self.pickup_at:
            raise RuntimeError('pickup_at is not set')
        return self.pickup_at - self.reached_pickup_at

    @property
    def scheduled_pickup_at(self) -> datetime.datetime:
        """Point in time at which the pickup was scheduled."""
        if not self.restaurant_notified_at:
            raise RuntimeError('restaurant_notified_at is not set')
        if not self.estimated_prep_duration:
            raise RuntimeError('estimated_prep_duration is not set')
        delta = datetime.timedelta(seconds=self.estimated_prep_duration)
        return self.restaurant_notified_at + delta

    @property
    def courier_early(self) -> datetime.timedelta:
        """Time by which a courier is early for pickup.

        Measured relative to Order.scheduled_pickup_at.

        0 if the courier is on time or late.

        Goes together with Order.courier_late.
        """
        return max(
            datetime.timedelta(), self.scheduled_pickup_at - self.reached_pickup_at,
        )

    @property
    def courier_late(self) -> datetime.timedelta:
        """Time by which a courier is late for pickup.

        Measured relative to Order.scheduled_pickup_at.

        0 if the courier is on time or early.

        Goes together with Order.courier_early.
        """
        return max(
            datetime.timedelta(), self.reached_pickup_at - self.scheduled_pickup_at,
        )

    @property
    def restaurant_early(self) -> datetime.timedelta:
        """Time by which a restaurant is early for pickup.

        Measured relative to Order.scheduled_pickup_at.

        0 if the restaurant is on time or late.

        Goes together with Order.restaurant_late.
        """
        return max(datetime.timedelta(), self.scheduled_pickup_at - self.pickup_at)

    @property
    def restaurant_late(self) -> datetime.timedelta:
        """Time by which a restaurant is late for pickup.

        Measured relative to Order.scheduled_pickup_at.

        0 if the restaurant is on time or early.

        Goes together with Order.restaurant_early.
        """
        return max(datetime.timedelta(), self.pickup_at - self.scheduled_pickup_at)

    @property
    def time_to_delivery(self) -> datetime.timedelta:
        """Time a courier took from pickup to delivery location."""
        if not self.pickup_at:
            raise RuntimeError('pickup_at is not set')
        if not self.reached_delivery_at:
            raise RuntimeError('reached_delivery_at is not set')
        return self.reached_delivery_at - self.pickup_at

    @property
    def time_at_delivery(self) -> datetime.timedelta:
        """Time a courier stayed at the delivery location."""
        if not self.reached_delivery_at:
            raise RuntimeError('reached_delivery_at is not set')
        if not self.delivery_at:
            raise RuntimeError('delivery_at is not set')
        return self.delivery_at - self.reached_delivery_at

    @property
    def courier_waited_at_delivery(self) -> datetime.timedelta:
        """Time a courier waited at the delivery location."""
        if self._courier_waited_at_delivery:
            return self.time_at_delivery
        return datetime.timedelta()

    @property
    def delivery_early(self) -> datetime.timedelta:
        """Time by which a scheduled order was early.

        Measured relative to Order.scheduled_delivery_at.

        0 if the delivery is on time or late.

        Goes together with Order.delivery_late.
        """
        if not self.scheduled:
            raise AttributeError('Makes sense only for scheduled orders')
        return max(datetime.timedelta(), self.scheduled_delivery_at - self.delivery_at)

    @property
    def delivery_late(self) -> datetime.timedelta:
        """Time by which a scheduled order was late.

        Measured relative to Order.scheduled_delivery_at.

        0 if the delivery is on time or early.

        Goes together with Order.delivery_early.
        """
        if not self.scheduled:
            raise AttributeError('Makes sense only for scheduled orders')
        return max(datetime.timedelta(), self.delivery_at - self.scheduled_delivery_at)

    @property
    def total_time(self) -> datetime.timedelta:
        """Time from order placement to delivery for an ad-hoc order."""
        if self.scheduled:
            raise AttributeError('Scheduled orders have no total_time')
        if self.cancelled:
            raise RuntimeError('Cancelled orders have no total_time')
        return self.delivery_at - self.placed_at

    # Other Methods

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}(#{order_id})>'.format(
            cls=self.__class__.__name__, order_id=self.id,
        )
