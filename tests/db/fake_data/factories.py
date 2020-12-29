"""Factories to create instances for the SQLAlchemy models."""

import datetime as dt
import random
import string

import factory
import faker
from factory import alchemy
from geopy import distance

from urban_meal_delivery import db


def _random_timespan(  # noqa:WPS211
    *,
    min_hours=0,
    min_minutes=0,
    min_seconds=0,
    max_hours=0,
    max_minutes=0,
    max_seconds=0,
):
    """A randomized `timedelta` object between the specified arguments."""
    total_min_seconds = min_hours * 3600 + min_minutes * 60 + min_seconds
    total_max_seconds = max_hours * 3600 + max_minutes * 60 + max_seconds
    return dt.timedelta(seconds=random.randint(total_min_seconds, total_max_seconds))


# The test day.
_YEAR, _MONTH, _DAY = 2020, 1, 1


def _early_in_the_morning():
    """A randomized `datetime` object early in the morning."""
    return dt.datetime(_YEAR, _MONTH, _DAY, 3, 0) + _random_timespan(max_hours=2)


class AddressFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Address` model."""

    class Meta:
        model = db.Address
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    created_at = factory.LazyFunction(_early_in_the_morning)

    # When testing, all addresses are considered primary ones.
    # As non-primary addresses have no different behavior and
    # the property is only kept from the original dataset for
    # completeness sake, that is ok to do.
    _primary_id = factory.LazyAttribute(lambda obj: obj.id)

    # Mimic a Google Maps Place ID with just random characters.
    place_id = factory.LazyFunction(
        lambda: ''.join(random.choice(string.ascii_lowercase) for _ in range(20)),
    )

    # Place the addresses somewhere in downtown Paris.
    latitude = factory.Faker('coordinate', center=48.855, radius=0.01)
    longitude = factory.Faker('coordinate', center=2.34, radius=0.03)
    # city -> set by the `make_address` fixture as there is only one `city`
    city_name = 'Paris'
    zip_code = factory.LazyFunction(lambda: random.randint(75001, 75020))
    street = factory.Faker('street_address', locale='fr_FR')


class CourierFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Courier` model."""

    class Meta:
        model = db.Courier
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    created_at = factory.LazyFunction(_early_in_the_morning)
    vehicle = 'bicycle'
    historic_speed = 7.89
    capacity = 100
    pay_per_hour = 750
    pay_per_order = 200


class CustomerFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Customer` model."""

    class Meta:
        model = db.Customer
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125


_restaurant_names = faker.Faker()


class RestaurantFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Restaurant` model."""

    class Meta:
        model = db.Restaurant
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    created_at = factory.LazyFunction(_early_in_the_morning)
    name = factory.LazyFunction(
        lambda: f"{_restaurant_names.first_name()}'s Restaurant",
    )
    # address -> set by the `make_restaurant` fixture as there is only one `city`
    estimated_prep_duration = 1000


class AdHocOrderFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Order` model.

    This factory creates ad-hoc `Order`s while the `ScheduledOrderFactory`
    below creates pre-orders. They are split into two classes mainly
    because the logic regarding how the timestamps are calculated from
    each other differs.

    See the docstring in the contained `Params` class for
    flags to adapt how the `Order` is created.
    """

    # pylint:disable=too-many-instance-attributes

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
                + _random_timespan(
                    max_seconds=(obj.pickup_at - obj.dispatch_at).total_seconds(),
                ),
            ),
        )
        cancel_after_pickup = factory.Trait(
            cancel_=True,
            cancelled_at=factory.LazyAttribute(
                lambda obj: obj.pickup_at
                + _random_timespan(
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
        lambda: dt.datetime(_YEAR, _MONTH, _DAY, 11, 45)
        + _random_timespan(max_hours=2, max_minutes=30),
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
        lambda obj: obj.placed_at + _random_timespan(min_seconds=30, max_seconds=90),
    )
    restaurant_notified_at_corrected = False
    restaurant_confirmed_at = factory.LazyAttribute(
        lambda obj: obj.restaurant_notified_at
        + _random_timespan(min_seconds=30, max_seconds=150),
    )
    restaurant_confirmed_at_corrected = False
    # Use the database defaults of the historic data.
    estimated_prep_duration = 900
    estimated_prep_duration_corrected = False
    estimated_prep_buffer = 480

    # Dispatch-related columns
    # courier -> set by the `make_order` fixture for better control
    dispatch_at = factory.LazyAttribute(
        lambda obj: obj.placed_at + _random_timespan(min_seconds=600, max_seconds=1080),
    )
    dispatch_at_corrected = False
    courier_notified_at = factory.LazyAttribute(
        lambda obj: obj.dispatch_at
        + _random_timespan(min_seconds=100, max_seconds=140),
    )
    courier_notified_at_corrected = False
    courier_accepted_at = factory.LazyAttribute(
        lambda obj: obj.courier_notified_at
        + _random_timespan(min_seconds=15, max_seconds=45),
    )
    courier_accepted_at_corrected = False
    # Sample a realistic utilization.
    utilization = factory.LazyFunction(lambda: random.choice([50, 60, 70, 80, 90, 100]))

    # Pickup-related attributes
    # pickup_address -> aligned with `restaurant.address` by the `make_order` fixture
    reached_pickup_at = factory.LazyAttribute(
        lambda obj: obj.courier_accepted_at
        + _random_timespan(min_seconds=300, max_seconds=600),
    )
    pickup_at = factory.LazyAttribute(
        lambda obj: obj.reached_pickup_at
        + _random_timespan(min_seconds=120, max_seconds=600),
    )
    pickup_at_corrected = False
    pickup_not_confirmed = False
    left_pickup_at = factory.LazyAttribute(
        lambda obj: obj.pickup_at + _random_timespan(min_seconds=60, max_seconds=180),
    )
    left_pickup_at_corrected = False

    # Delivery-related attributes
    # delivery_address -> set by the `make_order` fixture as there is only one `city`
    reached_delivery_at = factory.LazyAttribute(
        lambda obj: obj.left_pickup_at
        + _random_timespan(min_seconds=240, max_seconds=480),
    )
    delivery_at = factory.LazyAttribute(
        lambda obj: obj.reached_delivery_at
        + _random_timespan(min_seconds=240, max_seconds=660),
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
    def post(  # noqa:C901,WPS23 pylint:disable=unused-argument
        obj, create, extracted, **kwargs,  # noqa:B902,N805
    ):
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
                obj._courier_waited_at_delivery = None  # noqa:WPS437


class ScheduledOrderFactory(AdHocOrderFactory):
    """Create instances of the `db.Order` model.

    This class takes care of the various timestamps for pre-orders.

    Pre-orders are placed long before the test day's lunch time starts.
    All timestamps are relative to either `.dispatch_at` or `.restaurant_notified_at`
    and calculated backwards from `.scheduled_delivery_at`.
    """

    # Attributes regarding the specialization of an `Order`: ad-hoc or scheduled.
    placed_at = factory.LazyFunction(_early_in_the_morning)
    ad_hoc = False
    # Discrete `datetime` objects in the "core" lunch time are enough.
    scheduled_delivery_at = factory.LazyFunction(
        lambda: random.choice(
            [
                dt.datetime(_YEAR, _MONTH, _DAY, 12, 0),
                dt.datetime(_YEAR, _MONTH, _DAY, 12, 15),
                dt.datetime(_YEAR, _MONTH, _DAY, 12, 30),
                dt.datetime(_YEAR, _MONTH, _DAY, 12, 45),
                dt.datetime(_YEAR, _MONTH, _DAY, 13, 0),
                dt.datetime(_YEAR, _MONTH, _DAY, 13, 15),
                dt.datetime(_YEAR, _MONTH, _DAY, 13, 30),
            ],
        ),
    )
    scheduled_delivery_at_corrected = False
    # Assume the `Order` is on time.
    first_estimated_delivery_at = factory.LazyAttribute(
        lambda obj: obj.scheduled_delivery_at,
    )

    # Restaurant-related attributes
    restaurant_notified_at = factory.LazyAttribute(
        lambda obj: obj.scheduled_delivery_at
        - _random_timespan(min_minutes=45, max_minutes=50),
    )

    # Dispatch-related attributes
    dispatch_at = factory.LazyAttribute(
        lambda obj: obj.scheduled_delivery_at
        - _random_timespan(min_minutes=40, max_minutes=45),
    )
