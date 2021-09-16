"""Factory to create `Order` and `ReplayedOrder` instances."""

import datetime as dt

import factory
from factory import alchemy

from tests.db.fake_data.factories import utils
from urban_meal_delivery import db


class ReplayedOrderFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.ReplayedOrder` model.

    For simplicity, we assume the underlying `.order` to be an ad-hoc `Order`.
    """

    class Meta:
        model = db.ReplayedOrder
        sqlalchemy_get_or_create = ('simulation_id', 'order_id')

    # Generic columns
    # simulation -> set by the `make_replay_order` fixture for better control
    # actual (`Order`) -> set by the `make_replay_order` fixture for better control

    # `Order`-type related columns
    ad_hoc = factory.LazyAttribute(lambda obj: obj.actual.ad_hoc)
    placed_at = factory.LazyAttribute(lambda obj: obj.actual.placed_at)
    scheduled_delivery_at = factory.LazyAttribute(
        lambda obj: obj.actual.scheduled_delivery_at,
    )
    cancelled_at = None

    # Restaurant-related columns
    estimated_prep_duration = 1200
    restaurant_notified_at = factory.LazyAttribute(
        lambda obj: obj.placed_at
        + utils.random_timespan(min_seconds=1, max_seconds=30),
    )
    restaurant_confirmed_at = factory.LazyAttribute(
        lambda obj: obj.restaurant_notified_at
        + utils.random_timespan(min_seconds=1, max_seconds=60),
    )
    restaurant_ready_at = factory.LazyAttribute(
        lambda obj: obj.restaurant_confirmed_at
        + dt.timedelta(seconds=obj.estimated_prep_duration)
        + utils.random_timespan(min_seconds=300, max_seconds=300),
    )

    # Dispatch-related columns
    dispatch_at = factory.LazyAttribute(
        lambda obj: obj.actual.placed_at
        + utils.random_timespan(min_seconds=30, max_seconds=60),
    )
    first_estimated_delivery_at = factory.LazyAttribute(
        lambda obj: obj.restaurant_notified_at
        + dt.timedelta(seconds=obj.estimated_prep_duration)
        + dt.timedelta(minutes=10),
    )
    # courier -> set by the `make_replay_order` fixture for better control
    courier_notified_at = factory.LazyAttribute(
        lambda obj: obj.dispatch_at
        + utils.random_timespan(min_seconds=1, max_seconds=30),
    )
    courier_accepted_at = factory.LazyAttribute(
        lambda obj: obj.courier_notified_at
        + utils.random_timespan(min_seconds=1, max_seconds=60),
    )
    utilization = None

    # Pickup-related columns
    reached_pickup_at = factory.LazyAttribute(
        lambda obj: obj.restaurant_ready_at
        + utils.random_timespan(min_seconds=1, max_seconds=60),
    )
    pickup_at = factory.LazyAttribute(
        lambda obj: obj.reached_pickup_at
        + utils.random_timespan(min_seconds=30, max_seconds=60),
    )
    left_pickup_at = factory.LazyAttribute(
        lambda obj: obj.pickup_at
        + utils.random_timespan(min_seconds=30, max_seconds=60),
    )

    # Delivery-related columns
    reached_delivery_at = factory.LazyAttribute(
        lambda obj: obj.left_pickup_at
        + utils.random_timespan(min_minutes=5, max_minutes=10),
    )
    delivery_at = factory.LazyAttribute(
        lambda obj: obj.reached_delivery_at
        + utils.random_timespan(min_seconds=30, max_seconds=60),
    )

    @factory.post_generation
    def post(obj, _create, _extracted, **_kwargs):  # noqa:B902,C901,N805
        """Discard timestamps that occur after cancellation."""
        if obj.cancelled_at:
            if obj.cancelled_at <= obj.restaurant_notified_at:
                obj.restaurant_notified_at = None
            if obj.cancelled_at <= obj.restaurant_confirmed_at:
                obj.restaurant_confirmed_at = None
            if obj.cancelled_at <= obj.restaurant_ready_at:
                obj.restaurant_ready_at = None
            if obj.cancelled_at <= obj.dispatch_at:
                obj.dispatch_at = None
            if obj.cancelled_at <= obj.courier_notified_at:
                obj.courier_notified_at = None
            if obj.cancelled_at <= obj.courier_accepted_at:
                obj.courier_accepted_at = None
            if obj.cancelled_at <= obj.reached_pickup_at:
                obj.reached_pickup_at = None
            if obj.cancelled_at <= obj.pickup_at:
                obj.pickup_at = None
            if obj.cancelled_at <= obj.left_pickup_at:
                obj.left_pickup_at = None
            if obj.cancelled_at <= obj.reached_delivery_at:
                obj.reached_delivery_at = None
            if obj.cancelled_at <= obj.delivery_at:
                obj.delivery_at = None
