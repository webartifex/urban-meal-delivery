"""Provide the ORM's `ReplayedOrder` model for the replay simulations."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery.db import meta


class ReplayedOrder(meta.Base):
    """A simulated order by a `Customer` of the UDP."""

    __tablename__ = 'replayed_orders'

    # Generic columns
    simulation_id = sa.Column(sa.Integer, primary_key=True)
    actual_order_id = sa.Column(sa.Integer, primary_key=True)

    # `Order`-type related columns
    # `.ad_hoc` is part of a `ForeignKeyConstraint` to ensure the type
    # of the `ReplayedOrder` (i.e., ad-hoc or scheduled) is in line
    # with the `.actual` order.
    ad_hoc = sa.Column(sa.Boolean, nullable=False)
    placed_at = sa.Column(sa.DateTime, nullable=False)
    # Depending on `.ad_hoc`, `.scheduled_delivery_at` is either filled in or not.
    scheduled_delivery_at = sa.Column(sa.DateTime)
    # If an order is cancelled in a simulation,
    # some of the columns below do not apply any more.
    cancelled_at = sa.Column(sa.DateTime)

    # Restaurant-related columns
    estimated_prep_duration = sa.Column(sa.SmallInteger)
    restaurant_notified_at = sa.Column(sa.DateTime)
    restaurant_confirmed_at = sa.Column(sa.DateTime)
    restaurant_ready_at = sa.Column(sa.DateTime)

    # Dispatch-related columns
    dispatch_at = sa.Column(sa.DateTime)
    first_estimated_delivery_at = sa.Column(sa.DateTime)
    courier_id = sa.Column(sa.Integer, index=True)
    courier_notified_at = sa.Column(sa.DateTime)
    courier_accepted_at = sa.Column(sa.DateTime)
    utilization = sa.Column(sa.SmallInteger)

    # Pickup-related columns
    reached_pickup_at = sa.Column(sa.DateTime)
    pickup_at = sa.Column(sa.DateTime)
    left_pickup_at = sa.Column(sa.DateTime)

    # Delivery-related columns
    reached_delivery_at = sa.Column(sa.DateTime)
    delivery_at = sa.Column(sa.DateTime)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['simulation_id'],
            ['replay_simulations.id'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['actual_order_id', 'ad_hoc'],
            ['orders.id', 'orders.ad_hoc'],
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['courier_id'], ['couriers.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        # The check constraints model some of the assumptions made in the simulations.
        sa.CheckConstraint(
            # Align the order's type, ad-hoc or scheduled, with the type of the
            # `.actual` order and ensure the corresponding datetime column is set
            # or not set.
            """
                (
                    ad_hoc IS TRUE
                    AND
                    scheduled_delivery_at IS NULL
                )
                OR
                (
                    ad_hoc IS FALSE
                    AND
                    scheduled_delivery_at IS NOT NULL
                )
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
                (
                    EXTRACT(MINUTES FROM scheduled_delivery_at)::INTEGER
                    % 15 = 0
                )
                AND
                (
                    EXTRACT(SECONDS FROM scheduled_delivery_at)::INTEGER
                    = 0
                )
            """,
            name='scheduled_orders_must_be_at_quarters_of_an_hour',
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
            # A simulation must fill in at least all the timing and dispatch related
            # columns, unless an order is cancelled in a run.
            # Only `.estimated_prep_duration`, `.first_estimated_delivery_at`, and
            # `.utilization` are truly optional.
            # This constraint does allow missing columns for cancelled orders
            # in any combination of the below columns. So, no precedence constraints
            # are enforced (e.g., `.restaurant_notified_at` and `.restaurant_ready_at`
            # could be set without `.restaurant_confirmed_at`). That is acceptable
            # as cancelled orders are left out in the optimized KPIs.
            """
                cancelled_at IS NOT NULL
                OR
                (
                    restaurant_notified_at IS NOT NULL
                    AND
                    restaurant_confirmed_at IS NOT NULL
                    AND
                    restaurant_ready_at IS NOT NULL
                    AND
                    dispatch_at IS NOT NULL
                    AND
                    courier_id IS NOT NULL
                    AND
                    courier_notified_at IS NOT NULL
                    AND
                    courier_accepted_at IS NOT NULL
                    AND
                    reached_pickup_at IS NOT NULL
                    AND
                    pickup_at IS NOT NULL
                    AND
                    left_pickup_at IS NOT NULL
                    AND
                    reached_delivery_at IS NOT NULL
                    AND
                    delivery_at IS NOT NULL
                )
            """,
            name='orders_must_be_either_cancelled_or_fully_simulated',
        ),
        sa.CheckConstraint(
            # 23,487 out of the 660,608 orders were cancelled. In 685 of them, the
            # cancellation occurred after the pickup (as modeled by the `.pickup_at`
            # and `.left_pickup_at` columns, where the latter may be set with the
            # former being unset). As a simplification, we only allow cancellations
            # before the pickup in the simulations. Then, the restaurant throws away
            # the meal and the courier is free for other orders right away. Orders
            # cancelled after pickup in the actual data are assumed to be delivered
            # to the customer's door (and then still accepted or thrown away by the
            # customer). So, the courier becomes free only after the "fake" delivery.
            """
                NOT (  -- Only occurred in 528 of 660,608 orders in the actual data.
                    cancelled_at IS NOT NULL
                    AND
                    pickup_at IS NOT NULL
                )
                AND
                NOT (  -- Only occurred in 176 of 660,608 orders in the actual data.
                    cancelled_at IS NOT NULL
                    AND
                    left_pickup_at IS NOT NULL
                )
                AND
                NOT (  -- Never occurred in the actual data.
                    cancelled_at IS NOT NULL
                    AND
                    reached_delivery_at IS NOT NULL
                )
                AND
                NOT (  -- Never occurred in the actual data.
                    cancelled_at IS NOT NULL
                    AND
                    delivery_at IS NOT NULL
                )
            """,
            name='cancellations_may_only_occur_before_pickup',
        ),
        sa.CheckConstraint(
            # The actual `.estimated_prep_duration` and `.estimated_prep_buffer`
            # are modeled together as only one value. Therefore, the individual
            # upper limits of 2700 and 900 are added and result in 3600.
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 3600',
            name='estimated_prep_duration_between_0_and_3600',
        ),
        sa.CheckConstraint(
            # We still round estimates of the preparation time to whole minutes.
            # Other estimates are unlikely to change the simulation results in
            # a significant way.
            'estimated_prep_duration % 60 = 0',
            name='estimated_prep_duration_must_be_whole_minutes',
        ),
        sa.CheckConstraint(
            # If a simulation's `.strategy` models `.utilization`, it must be
            # realistic. The value can be deduced from the actual order's
            # courier's `.capacity` and the actual order's `.utilization`.
            '0 <= utilization AND utilization <= 100',
            name='utilization_between_0_and_100',
        ),
        sa.CheckConstraint(
            # The UDP is open from 11 am to 11 pm. So, before 11 am there is no
            # activity. After 11 pm, the last orders of a day are all assumed to be
            # dispatched before midnight.
            """
                NOT (
                    EXTRACT(HOUR FROM restaurant_notified_at) < 11
                    OR
                    EXTRACT(HOUR FROM dispatch_at) < 11
                )
            """,
            name='orders_dispatched_in_business_hours',
        ),
        *(
            # The timestamps must be in a logically correct order. That is the same as
            # in the actual `Order` model with an extra `restaurant_ready_at` column
            # and the non-simulated columns removed.
            sa.CheckConstraint(
                constraint, name='ordered_timestamps_{index}'.format(index=index),
            )
            for index, constraint in enumerate(
                (
                    'placed_at < scheduled_delivery_at',
                    'placed_at < cancelled_at',
                    'placed_at < restaurant_notified_at',
                    'placed_at < restaurant_confirmed_at',
                    'placed_at < restaurant_ready_at',
                    'placed_at < dispatch_at',
                    'placed_at < first_estimated_delivery_at',
                    'placed_at < courier_notified_at',
                    'placed_at < courier_accepted_at',
                    'placed_at < reached_pickup_at',
                    'placed_at < pickup_at',
                    'placed_at < left_pickup_at',
                    'placed_at < reached_delivery_at',
                    'placed_at < delivery_at',
                    'cancelled_at > restaurant_notified_at',
                    'cancelled_at > restaurant_confirmed_at',
                    'cancelled_at > restaurant_ready_at',
                    'cancelled_at > dispatch_at',
                    'cancelled_at > courier_notified_at',
                    'cancelled_at > courier_accepted_at',
                    'cancelled_at > reached_pickup_at',
                    'restaurant_notified_at < restaurant_confirmed_at',
                    'restaurant_notified_at < restaurant_ready_at',
                    'restaurant_notified_at < pickup_at',
                    'restaurant_confirmed_at < restaurant_ready_at',
                    'restaurant_confirmed_at < pickup_at',
                    'restaurant_ready_at < pickup_at',
                    'dispatch_at < first_estimated_delivery_at',
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
    simulation = orm.relationship('ReplaySimulation', back_populates='orders')
    actual = orm.relationship('Order', back_populates='replays')
    courier = orm.relationship('Courier')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}(#{order_id})>'.format(
            cls=self.__class__.__name__, order_id=self.actual.id,
        )

    # Convenience properties

    @property
    def customer(self) -> db.Customer:
        """`.customer` of the actual `Order`."""
        return self.actual.customer

    @property
    def restaurant(self) -> db.Restaurant:
        """`.restaurant` of the actual `Order`."""
        return self.actual.restaurant

    @property
    def pickup_address(self) -> db.Address:
        """`.pickup_address` of the actual `Order`."""
        return self.actual.pickup_address

    @property
    def delivery_address(self) -> db.Address:
        """`.delivery_address` of the actual `Order`."""
        return self.actual.delivery_address


from urban_meal_delivery import db  # noqa:E402  isort:skip
