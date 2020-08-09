"""Test the ORM's Order model."""

import datetime

import pytest
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in Order."""

    # pylint:disable=no-self-use

    def test_create_order(self, order_data):
        """Test instantiation of a new Order object."""
        result = db.Order(**order_data)

        assert result is not None

    def test_text_representation(self, order_data):
        """Order has a non-literal text representation."""
        order = db.Order(**order_data)
        id_ = order_data['id']

        result = repr(order)

        assert result == f'<Order(#{id_})>'


@pytest.mark.e2e
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in Order."""

    # pylint:disable=no-self-use

    def test_insert_into_database(self, order, db_session):
        """Insert an instance into the database."""
        db_session.add(order)
        db_session.commit()

    def test_dublicate_primary_key(self, order, order_data, city, db_session):
        """Can only add a record once."""
        db_session.add(order)
        db_session.commit()

        another_order = db.Order(**order_data)
        another_order.city = city
        db_session.add(another_order)

        with pytest.raises(orm_exc.FlushError):
            db_session.commit()

    # TODO (order-constraints): the various Foreign Key and Check Constraints
    # should be tested eventually. This is not of highest importance as
    # we have a lot of confidence from the data cleaning notebook.


class TestProperties:
    """Test properties in Order."""

    # pylint:disable=no-self-use,too-many-public-methods

    def test_is_not_scheduled(self, order_data):
        """Test Order.scheduled property."""
        order = db.Order(**order_data)

        result = order.scheduled

        assert result is False

    def test_is_scheduled(self, order_data):
        """Test Order.scheduled property."""
        order_data['ad_hoc'] = False
        order_data['scheduled_delivery_at'] = datetime.datetime(2020, 1, 2, 12, 30, 0)
        order_data['scheduled_delivery_at_corrected'] = False
        order = db.Order(**order_data)

        result = order.scheduled

        assert result is True

    def test_is_completed(self, order_data):
        """Test Order.completed property."""
        order = db.Order(**order_data)

        result = order.completed

        assert result is True

    def test_is_not_completed(self, order_data):
        """Test Order.completed property."""
        order_data['cancelled'] = True
        order_data['cancelled_at'] = datetime.datetime(2020, 1, 2, 12, 15, 0)
        order_data['cancelled_at_corrected'] = False
        order = db.Order(**order_data)

        result = order.completed

        assert result is False

    def test_is_corrected(self, order_data):
        """Test Order.corrected property."""
        order_data['dispatch_at_corrected'] = True
        order = db.Order(**order_data)

        result = order.corrected

        assert result is True

    def test_time_to_accept_no_dispatch_at(self, order_data):
        """Test Order.time_to_accept property."""
        order_data['dispatch_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_accept)

    def test_time_to_accept_no_courier_accepted(self, order_data):
        """Test Order.time_to_accept property."""
        order_data['courier_accepted_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_accept)

    def test_time_to_accept_success(self, order_data):
        """Test Order.time_to_accept property."""
        order = db.Order(**order_data)

        result = order.time_to_accept

        assert isinstance(result, datetime.timedelta)

    def test_time_to_react_no_courier_notified(self, order_data):
        """Test Order.time_to_react property."""
        order_data['courier_notified_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_react)

    def test_time_to_react_no_courier_accepted(self, order_data):
        """Test Order.time_to_react property."""
        order_data['courier_accepted_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_react)

    def test_time_to_react_success(self, order_data):
        """Test Order.time_to_react property."""
        order = db.Order(**order_data)

        result = order.time_to_react

        assert isinstance(result, datetime.timedelta)

    def test_time_to_pickup_no_reached_pickup_at(self, order_data):
        """Test Order.time_to_pickup property."""
        order_data['reached_pickup_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_pickup)

    def test_time_to_pickup_no_courier_accepted(self, order_data):
        """Test Order.time_to_pickup property."""
        order_data['courier_accepted_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_pickup)

    def test_time_to_pickup_success(self, order_data):
        """Test Order.time_to_pickup property."""
        order = db.Order(**order_data)

        result = order.time_to_pickup

        assert isinstance(result, datetime.timedelta)

    def test_time_at_pickup_no_reached_pickup_at(self, order_data):
        """Test Order.time_at_pickup property."""
        order_data['reached_pickup_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_pickup)

    def test_time_at_pickup_no_pickup_at(self, order_data):
        """Test Order.time_at_pickup property."""
        order_data['pickup_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_pickup)

    def test_time_at_pickup_success(self, order_data):
        """Test Order.time_at_pickup property."""
        order = db.Order(**order_data)

        result = order.time_at_pickup

        assert isinstance(result, datetime.timedelta)

    def test_scheduled_pickup_at_no_restaurant_notified(  # noqa:WPS118
        self, order_data,
    ):
        """Test Order.scheduled_pickup_at property."""
        order_data['restaurant_notified_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.scheduled_pickup_at)

    def test_scheduled_pickup_at_no_est_prep_duration(self, order_data):  # noqa:WPS118
        """Test Order.scheduled_pickup_at property."""
        order_data['estimated_prep_duration'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.scheduled_pickup_at)

    def test_scheduled_pickup_at_success(self, order_data):
        """Test Order.scheduled_pickup_at property."""
        order = db.Order(**order_data)

        result = order.scheduled_pickup_at

        assert isinstance(result, datetime.datetime)

    def test_if_courier_early_at_pickup(self, order_data):
        """Test Order.courier_early property."""
        order = db.Order(**order_data)

        result = order.courier_early

        assert bool(result) is True

    def test_if_courier_late_at_pickup(self, order_data):
        """Test Order.courier_late property."""
        # Opposite of test case before.
        order = db.Order(**order_data)

        result = order.courier_late

        assert bool(result) is False

    def test_if_restaurant_early_at_pickup(self, order_data):
        """Test Order.restaurant_early property."""
        order = db.Order(**order_data)

        result = order.restaurant_early

        assert bool(result) is True

    def test_if_restaurant_late_at_pickup(self, order_data):
        """Test Order.restaurant_late property."""
        # Opposite of test case before.
        order = db.Order(**order_data)

        result = order.restaurant_late

        assert bool(result) is False

    def test_time_to_delivery_no_reached_delivery_at(self, order_data):  # noqa:WPS118
        """Test Order.time_to_delivery property."""
        order_data['reached_delivery_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_delivery)

    def test_time_to_delivery_no_pickup_at(self, order_data):
        """Test Order.time_to_delivery property."""
        order_data['pickup_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_to_delivery)

    def test_time_to_delivery_success(self, order_data):
        """Test Order.time_to_delivery property."""
        order = db.Order(**order_data)

        result = order.time_to_delivery

        assert isinstance(result, datetime.timedelta)

    def test_time_at_delivery_no_reached_delivery_at(self, order_data):  # noqa:WPS118
        """Test Order.time_at_delivery property."""
        order_data['reached_delivery_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_delivery)

    def test_time_at_delivery_no_delivery_at(self, order_data):
        """Test Order.time_at_delivery property."""
        order_data['delivery_at'] = None
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='not set'):
            int(order.time_at_delivery)

    def test_time_at_delivery_success(self, order_data):
        """Test Order.time_at_delivery property."""
        order = db.Order(**order_data)

        result = order.time_at_delivery

        assert isinstance(result, datetime.timedelta)

    def test_courier_waited_at_delviery(self, order_data):
        """Test Order.courier_waited_at_delivery property."""
        order_data['_courier_waited_at_delivery'] = True
        order = db.Order(**order_data)

        result = int(order.courier_waited_at_delivery.total_seconds())

        assert result > 0

    def test_courier_did_not_wait_at_delivery(self, order_data):
        """Test Order.courier_waited_at_delivery property."""
        order_data['_courier_waited_at_delivery'] = False
        order = db.Order(**order_data)

        result = int(order.courier_waited_at_delivery.total_seconds())

        assert result == 0

    def test_if_delivery_early_success(self, order_data):
        """Test Order.delivery_early property."""
        order_data['ad_hoc'] = False
        order_data['scheduled_delivery_at'] = datetime.datetime(2020, 1, 2, 12, 30, 0)
        order_data['scheduled_delivery_at_corrected'] = False
        order = db.Order(**order_data)

        result = order.delivery_early

        assert bool(result) is True

    def test_if_delivery_early_failure(self, order_data):
        """Test Order.delivery_early property."""
        order = db.Order(**order_data)

        with pytest.raises(AttributeError, match='scheduled'):
            int(order.delivery_early)

    def test_if_delivery_late_success(self, order_data):
        """Test Order.delivery_late property."""
        order_data['ad_hoc'] = False
        order_data['scheduled_delivery_at'] = datetime.datetime(2020, 1, 2, 12, 30, 0)
        order_data['scheduled_delivery_at_corrected'] = False
        order = db.Order(**order_data)

        result = order.delivery_late

        assert bool(result) is False

    def test_if_delivery_late_failure(self, order_data):
        """Test Order.delivery_late property."""
        order = db.Order(**order_data)

        with pytest.raises(AttributeError, match='scheduled'):
            int(order.delivery_late)

    def test_no_total_time_for_pre_order(self, order_data):
        """Test Order.total_time property."""
        order_data['ad_hoc'] = False
        order_data['scheduled_delivery_at'] = datetime.datetime(2020, 1, 2, 12, 30, 0)
        order_data['scheduled_delivery_at_corrected'] = False
        order = db.Order(**order_data)

        with pytest.raises(AttributeError, match='Scheduled'):
            int(order.total_time)

    def test_no_total_time_for_cancelled_order(self, order_data):
        """Test Order.total_time property."""
        order_data['cancelled'] = True
        order_data['cancelled_at'] = datetime.datetime(2020, 1, 2, 12, 15, 0)
        order_data['cancelled_at_corrected'] = False
        order = db.Order(**order_data)

        with pytest.raises(RuntimeError, match='Cancelled'):
            int(order.total_time)

    def test_total_time_success(self, order_data):
        """Test Order.total_time property."""
        order = db.Order(**order_data)

        result = order.total_time

        assert isinstance(result, datetime.timedelta)
