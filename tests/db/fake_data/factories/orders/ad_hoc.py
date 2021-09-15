"""Factory to create ad-hoc `Order` instances."""

import datetime as dt
import random

import factory
from factory import alchemy
from geopy import distance

from tests import config as test_config
from tests.db.fake_data.factories import utils
from urban_meal_delivery import db


class AdHocOrderFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Order` model.

    This factory creates ad-hoc `Order`s while the `ScheduledOrderFactory`
    below creates pre-orders. They are split into two classes mainly
    because the logic regarding how the timestamps are calculated from
    each other differs.

    See the docstring in the contained `Params` class for
    flags to adapt how the `Order` is created.
    """

    class Meta:
        model = db.Order
        sqlalchemy_get_or_create = ('id',)

    class Params:
        """Define flags that overwrite some attributes.

        The `factory.Trait` objects in this class are executed after all
        the normal attributes in the `OrderFactory` classes were evaluated.

        Flags:
            cancel_before_pickup
            cancel_after_pickup
        """

        # Timestamps after `cancelled_at` are discarded
        # by the `post_generation` hook at the end of the `OrderFactory`.
        cancel_ = factory.Trait(  # noqa:WPS120 -> leading underscore does not work
            cancelled=True, cancelled_at_corrected=False,
        )
        cancel_before_pickup = factory.Trait(
            cancel_=True,
            cancelled_at=factory.LazyAttribute(
                lambda obj: obj.dispatch_at
                + utils.random_timespan(
                    max_seconds=(obj.pickup_at - obj.dispatch_at).total_seconds(),
                ),
            ),
        )
        cancel_after_pickup = factory.Trait(
            cancel_=True,
            cancelled_at=factory.LazyAttribute(
                lambda obj: obj.pickup_at
                + utils.random_timespan(
                    max_seconds=(obj.delivery_at - obj.pickup_at).total_seconds(),
                ),
            ),
        )

    # Generic attributes
    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    # customer -> set by the `make_order` fixture for better control

    # Attributes regarding the specialization of an `Order`: ad-hoc or scheduled.
    # Ad-hoc `Order`s are placed between 11.45 and 14.15.
    placed_at = factory.LazyFunction(
        lambda: dt.datetime(
            test_config.YEAR, test_config.MONTH, test_config.DAY, 11, 45,
        )
        + utils.random_timespan(max_hours=2, max_minutes=30),
    )
    ad_hoc = True
    scheduled_delivery_at = None
    scheduled_delivery_at_corrected = None
    # Without statistical info, we assume an ad-hoc `Order` delivered after 45 minutes.
    first_estimated_delivery_at = factory.LazyAttribute(
        lambda obj: obj.placed_at + dt.timedelta(minutes=45),
    )

    # Attributes regarding the cancellation of an `Order`.
    # May be overwritten with the `cancel_before_pickup` or `cancel_after_pickup` flags.
    cancelled = False
    cancelled_at = None
    cancelled_at_corrected = None

    # Price-related attributes -> sample realistic prices
    sub_total = factory.LazyFunction(lambda: 100 * random.randint(15, 25))
    delivery_fee = 250
    total = factory.LazyAttribute(lambda obj: obj.sub_total + obj.delivery_fee)

    # Restaurant-related attributes
    # restaurant -> set by the `make_order` fixture for better control
    restaurant_notified_at = factory.LazyAttribute(
        lambda obj: obj.placed_at
        + utils.random_timespan(min_seconds=30, max_seconds=90),
    )
    restaurant_notified_at_corrected = False
    restaurant_confirmed_at = factory.LazyAttribute(
        lambda obj: obj.restaurant_notified_at
        + utils.random_timespan(min_seconds=30, max_seconds=150),
    )
    restaurant_confirmed_at_corrected = False
    # Use the database defaults of the historic data.
    estimated_prep_duration = 900
    estimated_prep_duration_corrected = False
    estimated_prep_buffer = 480

    # Dispatch-related columns
    # courier -> set by the `make_order` fixture for better control
    dispatch_at = factory.LazyAttribute(
        lambda obj: obj.placed_at
        + utils.random_timespan(min_seconds=600, max_seconds=1080),
    )
    dispatch_at_corrected = False
    courier_notified_at = factory.LazyAttribute(
        lambda obj: obj.dispatch_at
        + utils.random_timespan(min_seconds=100, max_seconds=140),
    )
    courier_notified_at_corrected = False
    courier_accepted_at = factory.LazyAttribute(
        lambda obj: obj.courier_notified_at
        + utils.random_timespan(min_seconds=15, max_seconds=45),
    )
    courier_accepted_at_corrected = False
    # Sample a realistic utilization.
    utilization = factory.LazyFunction(lambda: random.choice([50, 60, 70, 80, 90, 100]))

    # Pickup-related attributes
    # pickup_address -> aligned with `restaurant.address` by the `make_order` fixture
    reached_pickup_at = factory.LazyAttribute(
        lambda obj: obj.courier_accepted_at
        + utils.random_timespan(min_seconds=300, max_seconds=600),
    )
    pickup_at = factory.LazyAttribute(
        lambda obj: obj.reached_pickup_at
        + utils.random_timespan(min_seconds=120, max_seconds=600),
    )
    pickup_at_corrected = False
    pickup_not_confirmed = False
    left_pickup_at = factory.LazyAttribute(
        lambda obj: obj.pickup_at
        + utils.random_timespan(min_seconds=60, max_seconds=180),
    )
    left_pickup_at_corrected = False

    # Delivery-related attributes
    # delivery_address -> set by the `make_order` fixture as there is only one `city`
    reached_delivery_at = factory.LazyAttribute(
        lambda obj: obj.left_pickup_at
        + utils.random_timespan(min_seconds=240, max_seconds=480),
    )
    delivery_at = factory.LazyAttribute(
        lambda obj: obj.reached_delivery_at
        + utils.random_timespan(min_seconds=240, max_seconds=660),
    )
    delivery_at_corrected = False
    delivery_not_confirmed = False
    _courier_waited_at_delivery = factory.LazyAttribute(
        lambda obj: False if obj.delivery_at else None,
    )

    # Statistical attributes -> calculate realistic stats
    logged_delivery_distance = factory.LazyAttribute(
        lambda obj: distance.great_circle(  # noqa:WPS317
            (obj.pickup_address.latitude, obj.pickup_address.longitude),
            (obj.delivery_address.latitude, obj.delivery_address.longitude),
        ).meters,
    )
    logged_avg_speed = factory.LazyAttribute(  # noqa:ECE001
        lambda obj: round(
            (
                obj.logged_avg_speed_distance
                / (obj.delivery_at - obj.pickup_at).total_seconds()
            ),
            2,
        ),
    )
    logged_avg_speed_distance = factory.LazyAttribute(
        lambda obj: 0.95 * obj.logged_delivery_distance,
    )

    @factory.post_generation
    def post(obj, _create, _extracted, **_kwargs):  # noqa:B902,C901,N805
        """Discard timestamps that occur after cancellation."""
        if obj.cancelled:
            if obj.cancelled_at <= obj.restaurant_notified_at:
                obj.restaurant_notified_at = None
                obj.restaurant_notified_at_corrected = None
            if obj.cancelled_at <= obj.restaurant_confirmed_at:
                obj.restaurant_confirmed_at = None
                obj.restaurant_confirmed_at_corrected = None
            if obj.cancelled_at <= obj.dispatch_at:
                obj.dispatch_at = None
                obj.dispatch_at_corrected = None
            if obj.cancelled_at <= obj.courier_notified_at:
                obj.courier_notified_at = None
                obj.courier_notified_at_corrected = None
            if obj.cancelled_at <= obj.courier_accepted_at:
                obj.courier_accepted_at = None
                obj.courier_accepted_at_corrected = None
            if obj.cancelled_at <= obj.reached_pickup_at:
                obj.reached_pickup_at = None
            if obj.cancelled_at <= obj.pickup_at:
                obj.pickup_at = None
                obj.pickup_at_corrected = None
                obj.pickup_not_confirmed = None
            if obj.cancelled_at <= obj.left_pickup_at:
                obj.left_pickup_at = None
                obj.left_pickup_at_corrected = None
            if obj.cancelled_at <= obj.reached_delivery_at:
                obj.reached_delivery_at = None
            if obj.cancelled_at <= obj.delivery_at:
                obj.delivery_at = None
                obj.delivery_at_corrected = None
                obj.delivery_not_confirmed = None
                obj._courier_waited_at_delivery = None
