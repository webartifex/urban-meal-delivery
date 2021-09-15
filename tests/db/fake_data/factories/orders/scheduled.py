"""Factory to create scheduled `Order` instances."""

import datetime as dt
import random

import factory

from tests import config as test_config
from tests.db.fake_data.factories import utils
from tests.db.fake_data.factories.orders import ad_hoc


class ScheduledOrderFactory(ad_hoc.AdHocOrderFactory):
    """Create instances of the `db.Order` model.

    This class takes care of the various timestamps for pre-orders.

    Pre-orders are placed long before the test day's lunch time starts.
    All timestamps are relative to either `.dispatch_at` or `.restaurant_notified_at`
    and calculated backwards from `.scheduled_delivery_at`.
    """

    # Attributes regarding the specialization of an `Order`: ad-hoc or scheduled.
    placed_at = factory.LazyFunction(utils.early_in_the_morning)
    ad_hoc = False
    # Discrete `datetime` objects in the "core" lunch time are enough.
    scheduled_delivery_at = factory.LazyFunction(
        lambda: random.choice(
            [
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 12, 0,
                ),
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 12, 15,
                ),
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 12, 30,
                ),
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 12, 45,
                ),
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 13, 0,
                ),
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 13, 15,
                ),
                dt.datetime(
                    test_config.YEAR, test_config.MONTH, test_config.DAY, 13, 30,
                ),
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
        - utils.random_timespan(min_minutes=45, max_minutes=50),
    )

    # Dispatch-related attributes
    dispatch_at = factory.LazyAttribute(
        lambda obj: obj.scheduled_delivery_at
        - utils.random_timespan(min_minutes=40, max_minutes=45),
    )
