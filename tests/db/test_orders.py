"""Test the ORM's `Order` model."""
# pylint:disable=no-self-use,protected-access

import datetime
import random

import pytest

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

    def test_insert_into_database(self, db_session, order):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Order).count() == 0

        db_session.add(order)
        db_session.commit()

        assert db_session.query(db.Order).count() == 1

    # TODO (order-constraints): the various Foreign Key and Check Constraints
    # should be tested eventually. This is not of highest importance as
    # we have a lot of confidence from the data cleaning notebook.


class TestProperties:
    """Test properties in `Order`.

    The `order` fixture uses the defaults specified in `factories.OrderFactory`
    and provided by the `make_order` fixture.
    """

    # pylint:disable=no-self-use,too-many-public-methods

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

        assert result > datetime.timedelta(0)

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

        assert result > datetime.timedelta(0)

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

        assert result > datetime.timedelta(0)

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

        assert result > datetime.timedelta(0)

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

        assert result > datetime.timedelta(0)

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

        assert result > datetime.timedelta(0)

    def test_courier_waited_at_delviery(self, order):
        """Test `Order.courier_waited_at_delivery` property."""
        order._courier_waited_at_delivery = True  # noqa:WPS437

        result = order.courier_waited_at_delivery.total_seconds()

        assert result > 0

    def test_courier_did_not_wait_at_delivery(self, order):
        """Test `Order.courier_waited_at_delivery` property."""
        order._courier_waited_at_delivery = False  # noqa:WPS437

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
        order.scheduled_delivery_at += datetime.timedelta(hours=2)

        result = order.delivery_early

        assert bool(result) is True

    def test_scheduled_order_not_delivered_early(self, make_order):
        """Test `Order.delivery_early` property."""
        order = make_order(scheduled=True)
        # Schedule the order to a lot earlier.
        order.scheduled_delivery_at -= datetime.timedelta(hours=2)

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
        order.scheduled_delivery_at -= datetime.timedelta(hours=2)

        result = order.delivery_late

        assert bool(result) is True

    def test_scheduled_order_not_delivered_late(self, make_order):
        """Test `Order.delivery_early` property."""
        order = make_order(scheduled=True)
        # Schedule the order to a lot later.
        order.scheduled_delivery_at += datetime.timedelta(hours=2)

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

        assert result > datetime.timedelta(0)


@pytest.mark.db
@pytest.mark.no_cover
def test_make_random_orders(  # noqa:C901,WPS211,WPS213,WPS231
    db_session, make_address, make_courier, make_restaurant, make_order,
):
    """Sanity check the all the `make_*` fixtures.

    Ensure that all generated `Address`, `Courier`, `Customer`, `Restauarant`,
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
