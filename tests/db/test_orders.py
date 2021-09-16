"""Test the ORM's `Order` model."""

import datetime as dt
import random

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from tests import config as test_config
from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `Order`."""

    def test_create_order(self, order):
        """Test instantiation of a new `Order` object."""
        assert order is not None

    def test_text_representation(self, order):
        """`Order` has a non-literal text representation."""
        result = repr(order)

        assert result == f'<Order(#{order.id})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Order`."""

    def test_insert_ad_hoc_order_into_into_database(self, db_session, order):
        """Insert an instance into the (empty) database."""
        assert order.ad_hoc is True

        assert db_session.query(db.Order).count() == 0

        db_session.add(order)
        db_session.commit()

        assert db_session.query(db.Order).count() == 1

    def test_insert_scheduled_order_into_into_database(self, db_session, pre_order):
        """Insert an instance into the (empty) database."""
        assert pre_order.ad_hoc is False

        assert db_session.query(db.Order).count() == 0

        db_session.add(pre_order)
        db_session.commit()

        assert db_session.query(db.Order).count() == 1

    def test_delete_a_referenced_customer(self, db_session, order):
        """Remove a record that is referenced with a FK."""
        db_session.add(order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Customer).where(db.Customer.id == order.customer.id)

        with pytest.raises(sa_exc.IntegrityError, match='fk_orders_to_customers'):
            db_session.execute(stmt)

    def test_delete_a_referenced_courier(self, db_session, order):
        """Remove a record that is referenced with a FK."""
        db_session.add(order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Courier).where(db.Courier.id == order.courier.id)

        with pytest.raises(sa_exc.IntegrityError, match='fk_orders_to_couriers'):
            db_session.execute(stmt)

    def test_delete_a_referenced_restaurant(self, db_session, order):
        """Remove a record that is referenced with a FK."""
        db_session.add(order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Restaurant).where(db.Restaurant.id == order.restaurant.id)

        with pytest.raises(sa_exc.IntegrityError, match='fk_orders_to_restaurants'):
            db_session.execute(stmt)

    def test_change_a_referenced_pickup_address(self, db_session, order, make_address):
        """Remove a record that is referenced with a FK.

        Each `Restaurant` may only have one `Address` in the dataset.
        """
        db_session.add(order)
        db_session.commit()

        # Give the `restaurant` another `address`.
        order.restaurant.address = make_address()
        db_session.add(order.restaurant.address)

        with pytest.raises(sa_exc.IntegrityError, match='fk_orders_to_restaurants'):
            db_session.commit()

    # Here should be a test to check deletion of a referenced pickup address, so
    # `test_delete_a_referenced_pickup_address(self, db_session, order)`.
    # The corresponding "fk_orders_to_addresses_on_pickup_address_id" constraint
    # is very hard to test in isolation as the above "fk_orders_to_restaurants_..."
    # constraint ensures its integrity already.

    def test_delete_a_referenced_delivery_address(self, db_session, order):
        """Remove a record that is referenced with a FK."""
        db_session.add(order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Address).where(db.Address.id == order.delivery_address.id)

        with pytest.raises(sa_exc.IntegrityError, match='fk_orders_to_addresses'):
            db_session.execute(stmt)

    def test_ad_hoc_order_with_scheduled_delivery_at(self, db_session, order):
        """Insert an instance with invalid data."""
        assert order.ad_hoc is True

        order.scheduled_delivery_at = dt.datetime(*test_config.DATE, 18, 0)
        order.scheduled_delivery_at_corrected = False

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='either_ad_hoc_or_scheduled_order',
        ):
            db_session.commit()

    def test_scheduled_order_without_scheduled_delivery_at(self, db_session, pre_order):
        """Insert an instance with invalid data."""
        assert pre_order.ad_hoc is False

        pre_order.scheduled_delivery_at = None
        pre_order.scheduled_delivery_at_corrected = None

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='either_ad_hoc_or_scheduled_order',
        ):
            db_session.commit()

    def test_ad_hoc_order_too_early(self, db_session, make_order):
        """Insert an instance with invalid data."""
        order = make_order(placed_at=dt.datetime(*test_config.DATE, 10, 0))

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='ad_hoc_orders_within_business_hours',
        ):
            db_session.commit()

    def test_ad_hoc_order_too_late(self, db_session, make_order):
        """Insert an instance with invalid data."""
        order = make_order(placed_at=dt.datetime(*test_config.DATE, 23, 0))

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='ad_hoc_orders_within_business_hours',
        ):
            db_session.commit()

    def test_scheduled_order_way_too_early(self, db_session, make_order):
        """Insert an instance with invalid data."""
        pre_order = make_order(
            scheduled=True, scheduled_delivery_at=dt.datetime(*test_config.DATE, 10, 0),
        )

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_within_business_hours',
        ):
            db_session.commit()

    def test_scheduled_order_a_bit_too_early(self, db_session, make_order):
        """Insert an instance with invalid data."""
        pre_order = make_order(
            scheduled=True,
            scheduled_delivery_at=dt.datetime(*test_config.DATE, 11, 30),
        )

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_within_business_hours',
        ):
            db_session.commit()

    def test_scheduled_order_not_too_early(self, db_session, make_order):
        """Insert an instance with invalid data.

        11.45 is the only time outside noon to 11 pm when a scheduled order is allowed.
        """
        pre_order = make_order(
            scheduled=True,
            scheduled_delivery_at=dt.datetime(*test_config.DATE, 11, 45),
        )

        assert db_session.query(db.Order).count() == 0

        db_session.add(pre_order)
        db_session.commit()

        assert db_session.query(db.Order).count() == 1

    def test_scheduled_order_too_late(self, db_session, make_order):
        """Insert an instance with invalid data."""
        pre_order = make_order(
            scheduled=True, scheduled_delivery_at=dt.datetime(*test_config.DATE, 23, 0),
        )

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_within_business_hours',
        ):
            db_session.commit()

    @pytest.mark.parametrize('minute', [min_ for min_ in range(60) if min_ % 15 != 0])
    def test_scheduled_order_at_non_quarter_of_an_hour(
        self, db_session, make_order, minute,
    ):
        """Insert an instance with invalid data."""
        pre_order = make_order(
            scheduled=True,
            scheduled_delivery_at=dt.datetime(  # `minute` is not 0, 15, 30, or 45
                *test_config.DATE, test_config.NOON, minute,
            ),
        )

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='scheduled_orders_must_be_at_quarters_of_an_hour',
        ):
            db_session.commit()

    @pytest.mark.parametrize('second', list(range(1, 60)))
    def test_scheduled_order_at_non_quarter_of_an_hour_by_seconds(
        self, db_session, make_order, second,
    ):
        """Insert an instance with invalid data."""
        pre_order = make_order(
            scheduled=True,
            scheduled_delivery_at=dt.datetime(
                *test_config.DATE, test_config.NOON, 0, second,
            ),
        )

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='scheduled_orders_must_be_at_quarters_of_an_hour',
        ):
            db_session.commit()

    def test_scheduled_order_too_soon(self, db_session, make_order):
        """Insert an instance with invalid data.

        Scheduled orders must be at least 30 minutes into the future.
        """
        # Create an ad-hoc order first and then make that a scheduled order.
        # This way, it is less work to keep the timestamps consistent.
        pre_order = make_order(scheduled=False)

        # Make the `scheduled_delivery_at` the quarter of an hour
        # following the next quarter of an hour (i.e., the timestamp
        # is between 15 and 30 minutes into the future).
        pre_order.ad_hoc = False
        minutes_to_next_quarter = 15 - (pre_order.placed_at.minute % 15)
        pre_order.scheduled_delivery_at = (
            # `.placed_at` may have non-0 seconds.
            pre_order.placed_at.replace(second=0)
            + dt.timedelta(minutes=(minutes_to_next_quarter + 15))
        )
        pre_order.scheduled_delivery_at_corrected = False

        db_session.add(pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_not_within_30_minutes',
        ):
            db_session.commit()

    def test_uncancelled_order_has_cancelled_at(self, db_session, order):
        """Insert an instance with invalid data."""
        order.cancelled_at = order.delivery_at
        order.cancelled_at_corrected = False
        order.delivery_at = None
        order.delivery_at_corrected = None
        order.delivery_not_confirmed = None
        order._courier_waited_at_delivery = None

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='only_cancelled_orders_may_have_cancelled_at',
        ):
            db_session.commit()

    def test_cancelled_order_is_delivered(self, db_session, order):
        """Insert an instance with invalid data."""
        order.cancelled = True
        order.cancelled_at = order.delivery_at + dt.timedelta(seconds=1)
        order.cancelled_at_corrected = False

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='cancelled_orders_must_not_be_delivered',
        ):
            db_session.commit()

    @pytest.mark.parametrize('duration', [-1, 2701])
    def test_estimated_prep_duration_out_of_range(self, db_session, order, duration):
        """Insert an instance with invalid data."""
        order.estimated_prep_duration = duration
        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='between_0_and_2700',
        ):
            db_session.commit()

    @pytest.mark.parametrize('duration', [1, 59, 119, 2699])
    def test_estimated_prep_duration_not_whole_minute(
        self, db_session, order, duration,
    ):
        """Insert an instance with invalid data."""
        order.estimated_prep_duration = duration
        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='must_be_whole_minutes',
        ):
            db_session.commit()

    @pytest.mark.parametrize('duration', [-1, 901])
    def test_estimated_prep_buffer_out_of_range(self, db_session, order, duration):
        """Insert an instance with invalid data."""
        order.estimated_prep_buffer = duration
        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='between_0_and_900',
        ):
            db_session.commit()

    @pytest.mark.parametrize('duration', [1, 59, 119, 899])
    def test_estimated_prep_buffer_not_whole_minute(self, db_session, order, duration):
        """Insert an instance with invalid data."""
        order.estimated_prep_buffer = duration
        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='must_be_whole_minutes',
        ):
            db_session.commit()

    @pytest.mark.parametrize('utilization', [-1, 101])
    def test_utilization_out_of_range(self, db_session, order, utilization):
        """Insert an instance with invalid data."""
        order.utilization = utilization
        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='between_0_and_100',
        ):
            db_session.commit()

    @pytest.mark.parametrize(
        'column',
        [
            'scheduled_delivery_at',
            'cancelled_at',
            'restaurant_notified_at',
            'restaurant_confirmed_at',
            'estimated_prep_duration',
            'dispatch_at',
            'courier_notified_at',
            'courier_accepted_at',
            'left_pickup_at',
        ],
    )
    def test_unset_timestamp_column_not_marked_as_uncorrected(  # noqa:WPS213
        self, db_session, order, column,
    ):
        """Insert an instance with invalid data.

        There are two special cases for this test case below,
        where other attributes on `order` must be unset.
        """
        # Set the actual timestamp to NULL.
        setattr(order, column, None)

        # Setting both the timestamp and its correction column to NULL is allowed.
        setattr(order, f'{column}_corrected', None)

        db_session.add(order)
        db_session.commit()

        # Also, an unset timestamp column may always be marked as corrected.
        setattr(order, f'{column}_corrected', True)

        db_session.add(order)
        db_session.commit()

        # Without a timestamp set, a column may not be marked as uncorrected.
        setattr(order, f'{column}_corrected', False)

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='corrections_only_for_set_value',
        ):
            db_session.commit()

    def test_unset_timestamp_column_not_marked_as_uncorrected_special_case1(
        self, db_session, order,
    ):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        order.pickup_not_confirmed = None
        self.test_unset_timestamp_column_not_marked_as_uncorrected(
            db_session, order, 'pickup_at',
        )

    def test_unset_timestamp_column_not_marked_as_uncorrected_special_case2(
        self, db_session, order,
    ):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        order.delivery_not_confirmed = None
        order._courier_waited_at_delivery = None
        self.test_unset_timestamp_column_not_marked_as_uncorrected(
            db_session, order, 'delivery_at',
        )

    @pytest.mark.parametrize(
        'column',
        [
            'restaurant_notified_at',
            'restaurant_confirmed_at',
            'estimated_prep_duration',
            'dispatch_at',
            'courier_notified_at',
            'courier_accepted_at',
            'pickup_at',
            'left_pickup_at',
            'delivery_at',
        ],
    )
    def test_set_timestamp_column_is_not_unmarked(  # noqa:WPS213
        self, db_session, order, column,
    ):
        """Insert an instance with invalid data.

        There are two special cases for this test case below,
        where other attributes on `order` must be unset.
        """
        # Ensure the timestamp is set.
        assert getattr(order, column) is not None

        # A set timestamp may be marked as either corrected or uncorrected.

        setattr(order, f'{column}_corrected', True)

        db_session.add(order)
        db_session.commit()

        setattr(order, f'{column}_corrected', False)

        db_session.add(order)
        db_session.commit()

        # A set timestamp may not be left unmarked.
        setattr(order, f'{column}_corrected', None)

        db_session.add(order)

        with pytest.raises(
            sa_exc.IntegrityError, match='corrections_only_for_set_value',
        ):
            db_session.commit()

    def test_set_timestamp_column_is_not_unmarked_special_case1(
        self, db_session, pre_order,
    ):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        self.test_set_timestamp_column_is_not_unmarked(
            db_session, pre_order, 'scheduled_delivery_at',
        )

    def test_set_timestamp_column_is_not_unmarked_special_case2(
        self, db_session, order,
    ):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        order.cancelled = True
        order.cancelled_at = order.delivery_at

        order.delivery_at = None
        order.delivery_at_corrected = None
        order.delivery_not_confirmed = None
        order._courier_waited_at_delivery = None

        self.test_set_timestamp_column_is_not_unmarked(
            db_session, order, 'cancelled_at',
        )

    @pytest.mark.parametrize(
        'comparison',
        [
            'placed_at < first_estimated_delivery_at',
            'placed_at < restaurant_notified_at',
            'placed_at < restaurant_confirmed_at',
            'placed_at < dispatch_at',
            'placed_at < courier_notified_at',
            'placed_at < courier_accepted_at',
            'placed_at < reached_pickup_at',
            'placed_at < pickup_at',
            'placed_at < left_pickup_at',
            'placed_at < reached_delivery_at',
            'placed_at < delivery_at',
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
        ],
    )
    def test_timestamps_unordered(
        self, db_session, order, comparison,
    ):
        """Insert an instance with invalid data.

        There are two special cases for this test case below,
        where other attributes on `order` must be unset.
        """
        smaller, bigger = comparison.split(' < ')

        assert smaller is not None

        violating_timestamp = getattr(order, smaller) - dt.timedelta(seconds=1)
        setattr(order, bigger, violating_timestamp)
        setattr(order, f'{bigger}_corrected', False)

        db_session.add(order)

        with pytest.raises(sa_exc.IntegrityError, match='ordered_timestamps'):
            db_session.commit()

    def test_timestamps_unordered_scheduled(self, db_session, pre_order):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        # As we subtract 1 second in the generic case,
        # choose one second after a quarter of an hour.
        pre_order.placed_at = dt.datetime(*test_config.DATE, 11, 45, 1)
        self.test_timestamps_unordered(
            db_session, pre_order, 'placed_at < scheduled_delivery_at',
        )

    @pytest.mark.parametrize(
        'comparison',
        [
            'placed_at < cancelled_at',
            'restaurant_notified_at < cancelled_at',
            'restaurant_confirmed_at < cancelled_at',
            'dispatch_at < cancelled_at',
            'courier_notified_at < cancelled_at',
            'courier_accepted_at < cancelled_at',
            'reached_pickup_at < cancelled_at',
            'pickup_at < cancelled_at',
            'left_pickup_at < cancelled_at',
            'reached_delivery_at < cancelled_at',
        ],
    )
    def test_timestamps_unordered_cancelled(
        self, db_session, order, comparison,
    ):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        order.cancelled = True

        order.delivery_at = None
        order.delivery_at_corrected = None
        order.delivery_not_confirmed = None
        order._courier_waited_at_delivery = None

        self.test_timestamps_unordered(db_session, order, comparison)


class TestProperties:
    """Test properties in `Order`.

    The `order` fixture uses the defaults specified in `factories.OrderFactory`
    and provided by the `make_order` fixture.
    """

    def test_is_ad_hoc(self, order):
        """Test `Order.scheduled` property."""
        assert order.ad_hoc is True

        result = order.scheduled

        assert result is False

    def test_is_scheduled(self, make_order):
        """Test `Order.scheduled` property."""
        order = make_order(scheduled=True)
        assert order.ad_hoc is False

        result = order.scheduled

        assert result is True

    def test_is_completed(self, order):
        """Test `Order.completed` property."""
        result = order.completed

        assert result is True

    def test_is_not_completed1(self, make_order):
        """Test `Order.completed` property."""
        order = make_order(cancel_before_pickup=True)
        assert order.cancelled is True

        result = order.completed

        assert result is False

    def test_is_not_completed2(self, make_order):
        """Test `Order.completed` property."""
        order = make_order(cancel_after_pickup=True)
        assert order.cancelled is True

        result = order.completed

        assert result is False

    def test_is_not_corrected(self, order):
        """Test `Order.corrected` property."""
        # By default, the `OrderFactory` sets all `.*_corrected` attributes to `False`.
        result = order.corrected

        assert result is False

    @pytest.mark.parametrize(
        'column',
        [
            'scheduled_delivery_at',
            'cancelled_at',
            'restaurant_notified_at',
            'restaurant_confirmed_at',
            'dispatch_at',
            'courier_notified_at',
            'courier_accepted_at',
            'pickup_at',
            'left_pickup_at',
            'delivery_at',
        ],
    )
    def test_is_corrected(self, order, column):
        """Test `Order.corrected` property."""
        setattr(order, f'{column}_corrected', True)

        result = order.corrected

        assert result is True

    def test_time_to_accept_no_dispatch_at(self, order):
        """Test `Order.time_to_accept` property."""
        order.dispatch_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_accept)

    def test_time_to_accept_no_courier_accepted(self, order):
        """Test `Order.time_to_accept` property."""
        order.courier_accepted_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_accept)

    def test_time_to_accept_success(self, order):
        """Test `Order.time_to_accept` property."""
        result = order.time_to_accept

        assert result > dt.timedelta(0)

    def test_time_to_react_no_courier_notified(self, order):
        """Test `Order.time_to_react` property."""
        order.courier_notified_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_react)

    def test_time_to_react_no_courier_accepted(self, order):
        """Test `Order.time_to_react` property."""
        order.courier_accepted_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_react)

    def test_time_to_react_success(self, order):
        """Test `Order.time_to_react` property."""
        result = order.time_to_react

        assert result > dt.timedelta(0)

    def test_time_to_pickup_no_reached_pickup_at(self, order):
        """Test `Order.time_to_pickup` property."""
        order.reached_pickup_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_pickup)

    def test_time_to_pickup_no_courier_accepted(self, order):
        """Test `Order.time_to_pickup` property."""
        order.courier_accepted_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_pickup)

    def test_time_to_pickup_success(self, order):
        """Test `Order.time_to_pickup` property."""
        result = order.time_to_pickup

        assert result > dt.timedelta(0)

    def test_time_at_pickup_no_reached_pickup_at(self, order):
        """Test `Order.time_at_pickup` property."""
        order.reached_pickup_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_pickup)

    def test_time_at_pickup_no_pickup_at(self, order):
        """Test `Order.time_at_pickup` property."""
        order.pickup_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_pickup)

    def test_time_at_pickup_success(self, order):
        """Test `Order.time_at_pickup` property."""
        result = order.time_at_pickup

        assert result > dt.timedelta(0)

    def test_scheduled_pickup_at_no_restaurant_notified(self, order):  # noqa:WPS118
        """Test `Order.scheduled_pickup_at` property."""
        order.restaurant_notified_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.scheduled_pickup_at)

    def test_scheduled_pickup_at_no_est_prep_duration(self, order):  # noqa:WPS118
        """Test `Order.scheduled_pickup_at` property."""
        order.estimated_prep_duration = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.scheduled_pickup_at)

    def test_scheduled_pickup_at_success(self, order):
        """Test `Order.scheduled_pickup_at` property."""
        result = order.scheduled_pickup_at

        assert order.placed_at < result < order.delivery_at

    def test_courier_is_early_at_pickup(self, order):
        """Test `Order.courier_early` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 999_999

        result = order.courier_early

        assert bool(result) is True

    def test_courier_is_not_early_at_pickup(self, order):
        """Test `Order.courier_early` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 1

        result = order.courier_early

        assert bool(result) is False

    def test_courier_is_late_at_pickup(self, order):
        """Test `Order.courier_late` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 1

        result = order.courier_late

        assert bool(result) is True

    def test_courier_is_not_late_at_pickup(self, order):
        """Test `Order.courier_late` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 999_999

        result = order.courier_late

        assert bool(result) is False

    def test_restaurant_early_at_pickup(self, order):
        """Test `Order.restaurant_early` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 999_999

        result = order.restaurant_early

        assert bool(result) is True

    def test_restaurant_is_not_early_at_pickup(self, order):
        """Test `Order.restaurant_early` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 1

        result = order.restaurant_early

        assert bool(result) is False

    def test_restaurant_is_late_at_pickup(self, order):
        """Test `Order.restaurant_late` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 1

        result = order.restaurant_late

        assert bool(result) is True

    def test_restaurant_is_not_late_at_pickup(self, order):
        """Test `Order.restaurant_late` property."""
        # Manipulate the attribute that determines `Order.scheduled_pickup_at`.
        order.estimated_prep_duration = 999_999

        result = order.restaurant_late

        assert bool(result) is False

    def test_time_to_delivery_no_reached_delivery_at(self, order):  # noqa:WPS118
        """Test `Order.time_to_delivery` property."""
        order.reached_delivery_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_delivery)

    def test_time_to_delivery_no_pickup_at(self, order):
        """Test `Order.time_to_delivery` property."""
        order.pickup_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_delivery)

    def test_time_to_delivery_success(self, order):
        """Test `Order.time_to_delivery` property."""
        result = order.time_to_delivery

        assert result > dt.timedelta(0)

    def test_time_at_delivery_no_reached_delivery_at(self, order):  # noqa:WPS118
        """Test `Order.time_at_delivery` property."""
        order.reached_delivery_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_delivery)

    def test_time_at_delivery_no_delivery_at(self, order):
        """Test `Order.time_at_delivery` property."""
        order.delivery_at = None

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_delivery)

    def test_time_at_delivery_success(self, order):
        """Test `Order.time_at_delivery` property."""
        result = order.time_at_delivery

        assert result > dt.timedelta(0)

    def test_courier_waited_at_delivery(self, order):
        """Test `Order.courier_waited_at_delivery` property."""
        order._courier_waited_at_delivery = True

        result = order.courier_waited_at_delivery.total_seconds()

        assert result > 0

    def test_courier_did_not_wait_at_delivery(self, order):
        """Test `Order.courier_waited_at_delivery` property."""
        order._courier_waited_at_delivery = False

        result = order.courier_waited_at_delivery.total_seconds()

        assert result == 0

    def test_ad_hoc_order_cannot_be_early(self, order):
        """Test `Order.delivery_early` property."""
        # By default, the `OrderFactory` creates ad-hoc orders.
        with pytest.raises(AttributeError, match='scheduled'):
            int(order.delivery_early)

    def test_scheduled_order_delivered_early(self, make_order):
        """Test `Order.delivery_early` property."""
        order = make_order(scheduled=True)
        # Schedule the order to a lot later.
        order.scheduled_delivery_at += dt.timedelta(hours=2)

        result = order.delivery_early

        assert bool(result) is True

    def test_scheduled_order_not_delivered_early(self, make_order):
        """Test `Order.delivery_early` property."""
        order = make_order(scheduled=True)
        # Schedule the order to a lot earlier.
        order.scheduled_delivery_at -= dt.timedelta(hours=2)

        result = order.delivery_early

        assert bool(result) is False

    def test_ad_hoc_order_cannot_be_late(self, order):
        """Test Order.delivery_late property."""
        # By default, the `OrderFactory` creates ad-hoc orders.
        with pytest.raises(AttributeError, match='scheduled'):
            int(order.delivery_late)

    def test_scheduled_order_delivered_late(self, make_order):
        """Test `Order.delivery_early` property."""
        order = make_order(scheduled=True)
        # Schedule the order to a lot earlier.
        order.scheduled_delivery_at -= dt.timedelta(hours=2)

        result = order.delivery_late

        assert bool(result) is True

    def test_scheduled_order_not_delivered_late(self, make_order):
        """Test `Order.delivery_early` property."""
        order = make_order(scheduled=True)
        # Schedule the order to a lot later.
        order.scheduled_delivery_at += dt.timedelta(hours=2)

        result = order.delivery_late

        assert bool(result) is False

    def test_no_total_time_for_scheduled_order(self, make_order):
        """Test `Order.total_time` property."""
        order = make_order(scheduled=True)

        with pytest.raises(AttributeError, match='Scheduled'):
            int(order.total_time)

    def test_no_total_time_for_cancelled_order(self, make_order):
        """Test `Order.total_time` property."""
        order = make_order(cancel_before_pickup=True)

        with pytest.raises(RuntimeError, match='Cancelled'):
            int(order.total_time)

    def test_total_time_success(self, order):
        """Test `Order.total_time` property."""
        result = order.total_time

        assert result > dt.timedelta(0)


@pytest.mark.db
@pytest.mark.no_cover
def test_make_random_orders(  # noqa:C901,WPS211,WPS213
    db_session, make_address, make_courier, make_restaurant, make_order,
):
    """Sanity check the all the `make_*` fixtures.

    Ensure that all generated `Address`, `Courier`, `Customer`, `Restaurant`,
    and `Order` objects adhere to the database constraints.
    """  # noqa:D202
    # Generate a large number of `Order`s to obtain a large variance of data.
    for _ in range(1_000):  # noqa:WPS122

        # Ad-hoc `Order`s are far more common than pre-orders.
        scheduled = random.choice([True, False, False, False, False])

        # Randomly pass a `address` argument to `make_restaurant()` and
        # a `restaurant` argument to `make_order()`.
        if random.random() < 0.5:
            address = random.choice([None, make_address()])
            restaurant = make_restaurant(address=address)
        else:
            restaurant = None

        # Randomly pass a `courier` argument to `make_order()`.
        courier = random.choice([None, make_courier()])

        # A tiny fraction of `Order`s get cancelled.
        if random.random() < 0.05:
            if random.random() < 0.5:
                cancel_before_pickup, cancel_after_pickup = True, False
            else:
                cancel_before_pickup, cancel_after_pickup = False, True
        else:
            cancel_before_pickup, cancel_after_pickup = False, False

        # Write all the generated objects to the database.
        # This should already trigger an `IntegrityError` if the data are flawed.
        order = make_order(
            scheduled=scheduled,
            restaurant=restaurant,
            courier=courier,
            cancel_before_pickup=cancel_before_pickup,
            cancel_after_pickup=cancel_after_pickup,
        )
        db_session.add(order)

    db_session.commit()
