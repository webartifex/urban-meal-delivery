"""Test the ORM's `ReplayedOrder` model."""

import datetime as dt

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from tests import config as test_config
from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `ReplayedOrder`."""

    def test_create_order(self, replayed_order):
        """Test instantiation of a new `ReplayedOrder` object."""
        assert replayed_order is not None

    def test_text_representation(self, replayed_order):
        """`ReplayedOrder` has a non-literal text representation."""
        result = repr(replayed_order)

        assert result == f'<ReplayedOrder(#{replayed_order.actual.id})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `ReplayedOrder`."""

    def test_insert_into_into_database(self, db_session, replayed_order):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.ReplayedOrder).count() == 0

        db_session.add(replayed_order)
        db_session.commit()

        assert db_session.query(db.ReplayedOrder).count() == 1

    def test_delete_a_referenced_simulation(self, db_session, replayed_order):
        """Remove a record that is referenced with a FK."""
        db_session.add(replayed_order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.ReplaySimulation).where(
            db.ReplaySimulation.id == replayed_order.simulation.id,
        )

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_replayed_orders_to_replay_simulations',
        ):
            db_session.execute(stmt)

    def test_delete_a_referenced_actual_order(self, db_session, replayed_order):
        """Remove a record that is referenced with a FK."""
        db_session.add(replayed_order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Order).where(db.Order.id == replayed_order.actual.id)

        with pytest.raises(sa_exc.IntegrityError, match='fk_replayed_orders_to_orders'):
            db_session.execute(stmt)

    def test_delete_a_referenced_courier(
        self, db_session, replayed_order, make_courier,
    ):
        """Remove a record that is referenced with a FK."""
        # Need a second courier, one that is
        # not associated with the `.actual` order.
        replayed_order.courier = make_courier()

        db_session.add(replayed_order)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Courier).where(db.Courier.id == replayed_order.courier.id)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_replayed_orders_to_couriers',
        ):
            db_session.execute(stmt)

    def test_ad_hoc_order_with_scheduled_delivery_at(self, db_session, replayed_order):
        """Insert an instance with invalid data."""
        assert replayed_order.ad_hoc is True

        replayed_order.scheduled_delivery_at = dt.datetime(*test_config.DATE, 18, 0)

        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='either_ad_hoc_or_scheduled_order',
        ):
            db_session.commit()

    def test_scheduled_order_without_scheduled_delivery_at(
        self, db_session, make_replay_order,
    ):
        """Insert an instance with invalid data."""
        replay_order = make_replay_order(scheduled=True)

        assert replay_order.ad_hoc is False

        replay_order.scheduled_delivery_at = None

        db_session.add(replay_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='either_ad_hoc_or_scheduled_order',
        ):
            db_session.commit()

    def test_ad_hoc_order_too_early(self, db_session, make_replay_order):
        """Insert an instance with invalid data."""
        replay_order = make_replay_order(
            placed_at=dt.datetime(*test_config.DATE, 10, 0),
        )

        db_session.add(replay_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='ad_hoc_orders_within_business_hours',
        ):
            db_session.commit()

    def test_ad_hoc_order_too_late(self, db_session, make_replay_order):
        """Insert an instance with invalid data."""
        replay_order = make_replay_order(
            placed_at=dt.datetime(*test_config.DATE, 23, 0),
        )

        db_session.add(replay_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='ad_hoc_orders_within_business_hours',
        ):
            db_session.commit()

    def test_scheduled_order_way_too_early(self, db_session, make_replay_order):
        """Insert an instance with invalid data."""
        scheduled_delivery_at = dt.datetime(*test_config.DATE, 10, 0)
        replay_pre_order = make_replay_order(
            scheduled=True,
            placed_at=scheduled_delivery_at - dt.timedelta(hours=12),
            scheduled_delivery_at=scheduled_delivery_at,
            restaurant_notified_at=scheduled_delivery_at + dt.timedelta(hours=1),
            dispatch_at=scheduled_delivery_at + dt.timedelta(hours=1),
        )

        db_session.add(replay_pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_within_business_hours',
        ):
            db_session.commit()

    def test_scheduled_order_a_bit_too_early(self, db_session, make_replay_order):
        """Insert an instance with invalid data."""
        scheduled_delivery_at = dt.datetime(*test_config.DATE, 11, 30)
        replay_pre_order = make_replay_order(
            scheduled=True,
            placed_at=scheduled_delivery_at - dt.timedelta(hours=14),
            scheduled_delivery_at=scheduled_delivery_at,
            restaurant_notified_at=scheduled_delivery_at + dt.timedelta(hours=1),
            dispatch_at=scheduled_delivery_at + dt.timedelta(hours=1),
        )

        db_session.add(replay_pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_within_business_hours',
        ):
            db_session.commit()

    def test_scheduled_order_not_too_early(self, db_session, make_replay_order):
        """Insert an instance with invalid data.

        11.45 is the only time outside noon to 11 pm when a scheduled order is allowed.
        """
        scheduled_delivery_at = dt.datetime(*test_config.DATE, 11, 45)
        replay_pre_order = make_replay_order(
            scheduled=True,
            placed_at=scheduled_delivery_at - dt.timedelta(hours=14),
            scheduled_delivery_at=scheduled_delivery_at,
            restaurant_notified_at=scheduled_delivery_at + dt.timedelta(hours=1),
            dispatch_at=scheduled_delivery_at + dt.timedelta(hours=1),
        )

        assert db_session.query(db.Order).count() == 0

        db_session.add(replay_pre_order)
        db_session.commit()

        assert db_session.query(db.Order).count() == 1

    def test_scheduled_order_too_late(self, db_session, make_replay_order):
        """Insert an instance with invalid data."""
        scheduled_delivery_at = dt.datetime(*test_config.DATE, 23, 0)
        replay_pre_order = make_replay_order(
            scheduled=True,
            placed_at=scheduled_delivery_at - dt.timedelta(hours=10),
            scheduled_delivery_at=scheduled_delivery_at,
            restaurant_notified_at=scheduled_delivery_at + dt.timedelta(minutes=30),
            dispatch_at=scheduled_delivery_at + dt.timedelta(minutes=30),
        )

        db_session.add(replay_pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_within_business_hours',
        ):
            db_session.commit()

    @pytest.mark.parametrize('minute', [min_ for min_ in range(60) if min_ % 15 != 0])
    def test_scheduled_order_at_non_quarter_of_an_hour(
        self, db_session, make_replay_order, minute,
    ):
        """Insert an instance with invalid data."""
        scheduled_delivery_at = dt.datetime(  # `minute` is not 0, 15, 30, or 45
            *test_config.DATE, test_config.NOON, minute,
        )
        replay_pre_order = make_replay_order(
            scheduled=True,
            placed_at=scheduled_delivery_at - dt.timedelta(hours=10),
            scheduled_delivery_at=scheduled_delivery_at,
            restaurant_notified_at=scheduled_delivery_at + dt.timedelta(minutes=30),
            dispatch_at=scheduled_delivery_at + dt.timedelta(minutes=30),
        )

        db_session.add(replay_pre_order)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='scheduled_orders_must_be_at_quart',  # constraint name too long
        ):
            db_session.commit()

    @pytest.mark.parametrize('second', list(range(1, 60)))
    def test_scheduled_order_at_non_quarter_of_an_hour_by_seconds(
        self, db_session, make_replay_order, second,
    ):
        """Insert an instance with invalid data."""
        scheduled_delivery_at = dt.datetime(
            *test_config.DATE, test_config.NOON, 0, second,
        )
        replay_pre_order = make_replay_order(
            scheduled=True,
            placed_at=scheduled_delivery_at - dt.timedelta(hours=10),
            scheduled_delivery_at=scheduled_delivery_at,
            restaurant_notified_at=scheduled_delivery_at + dt.timedelta(minutes=30),
            dispatch_at=scheduled_delivery_at + dt.timedelta(minutes=30),
        )

        db_session.add(replay_pre_order)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='scheduled_orders_must_be_at_quart',  # constraint name too long
        ):
            db_session.commit()

    def test_scheduled_order_too_soon(self, db_session, make_replay_order):
        """Insert an instance with invalid data.

        Scheduled orders must be at least 30 minutes into the future.
        """
        # Create an ad-hoc order first and then make that a scheduled order.
        # This way, it is less work to keep the timestamps consistent.
        replay_pre_order = make_replay_order(scheduled=False)

        # Make the `scheduled_delivery_at` the quarter of an hour
        # following the next quarter of an hour (i.e., the timestamp
        # is between 15 and 30 minutes into the future).
        replay_pre_order.ad_hoc = False
        replay_pre_order.actual.ad_hoc = False
        minutes_to_next_quarter = 15 - (replay_pre_order.placed_at.minute % 15)
        scheduled_delivery_at = (
            # `.placed_at` may have non-0 seconds.
            replay_pre_order.placed_at.replace(second=0)
            + dt.timedelta(minutes=(minutes_to_next_quarter + 15))
        )
        replay_pre_order.scheduled_delivery_at = scheduled_delivery_at
        replay_pre_order.actual.scheduled_delivery_at = scheduled_delivery_at
        replay_pre_order.actual.scheduled_delivery_at_corrected = False

        db_session.add(replay_pre_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='scheduled_orders_not_within_30_minutes',
        ):
            db_session.commit()

    @pytest.mark.parametrize(
        'column',
        [
            'restaurant_notified_at',
            'restaurant_confirmed_at',
            'restaurant_ready_at',
            'dispatch_at',
            'courier',  # not `.courier_id`
            'courier_notified_at',
            'courier_accepted_at',
            'reached_pickup_at',
            'pickup_at',
            'left_pickup_at',
            'reached_delivery_at',
            'delivery_at',
        ],
    )
    def test_not_fully_simulated_order(self, db_session, replayed_order, column):
        """Insert an instance with invalid data."""
        assert replayed_order.cancelled_at is None

        setattr(replayed_order, column, None)

        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='either_cancelled_o',  # constraint name too long
        ):
            db_session.commit()

    @pytest.mark.parametrize(
        'column',
        [
            'restaurant_notified_at',
            'restaurant_confirmed_at',
            'restaurant_ready_at',
            'dispatch_at',
            'courier_id',
            'courier_notified_at',
            'courier_accepted_at',
            'reached_pickup_at',
        ],
    )
    def test_simulated_cancellation(self, db_session, replayed_order, column):
        """Insert an instance with invalid data.

        Cancelled orders may have missing timestamps
        """
        replayed_order.cancelled_at = replayed_order.pickup_at

        replayed_order.pickup_at = None
        replayed_order.left_pickup_at = None
        replayed_order.reached_delivery_at = None
        replayed_order.delivery_at = None

        setattr(replayed_order, column, None)

        db_session.add(replayed_order)
        db_session.commit()

    @pytest.mark.parametrize(
        'column', ['pickup_at', 'left_pickup_at', 'reached_delivery_at', 'delivery_at'],
    )
    def test_no_simulated_cancellation_after_pickup(
        self, db_session, replayed_order, column,
    ):
        """Insert an instance with invalid data."""
        # Setting `.cancelled_at` to the end of a day
        # ensures the timestamps are logically ok.
        replayed_order.cancelled_at = dt.datetime(*test_config.DATE, 23)

        # Set all timestamps after `.reached_pickup_at` to NULL
        # except the one under test.
        for unset_column in (
            'pickup_at',
            'left_pickup_at',
            'reached_delivery_at',
            'delivery_at',
        ):
            if unset_column != column:
                setattr(replayed_order, unset_column, None)

        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='cancellations_may_only_occur_befo',  # constraint name too long
        ):
            db_session.commit()

    @pytest.mark.parametrize('duration', [-1, 3601])
    def test_estimated_prep_duration_out_of_range(
        self, db_session, replayed_order, duration,
    ):
        """Insert an instance with invalid data."""
        replayed_order.estimated_prep_duration = duration
        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='between_0',  # constraint name too long
        ):
            db_session.commit()

    @pytest.mark.parametrize('duration', [1, 59, 119, 3599])
    def test_estimated_prep_duration_not_whole_minute(
        self, db_session, replayed_order, duration,
    ):
        """Insert an instance with invalid data."""
        replayed_order.estimated_prep_duration = duration
        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='must_be_w',  # constraint name too long
        ):
            db_session.commit()

    @pytest.mark.parametrize('utilization', [-1, 101])
    def test_utilization_out_of_range(self, db_session, replayed_order, utilization):
        """Insert an instance with invalid data."""
        replayed_order.utilization = utilization
        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='between_0_and_100',
        ):
            db_session.commit()

    @pytest.mark.parametrize('column', ['restaurant_notified_at', 'dispatch_at'])
    @pytest.mark.parametrize('hour', [0, 10])
    def test_order_dispatched_in_non_business_hour(
        self, db_session, replayed_order, column, hour,
    ):
        """Insert an instance with invalid data."""
        orig_timestamp = getattr(replayed_order, column)
        new_timestamp = orig_timestamp.replace(hour=hour)

        replayed_order.placed_at = new_timestamp - dt.timedelta(minutes=1)
        setattr(replayed_order, column, new_timestamp)

        db_session.add(replayed_order)

        with pytest.raises(
            sa_exc.IntegrityError, match='business_hours',
        ):
            db_session.commit()

    @pytest.mark.parametrize(
        'comparison',
        [
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
        ],
    )
    def test_timestamps_unordered(
        self, db_session, replayed_order, comparison,
    ):
        """Insert an instance with invalid data.

        There are two special cases for this test case below,
        where other attributes on `replayed_order` must be unset.
        """
        smaller, bigger = comparison.split(' < ')

        assert smaller is not None

        violating_timestamp = getattr(replayed_order, smaller) - dt.timedelta(seconds=1)
        setattr(replayed_order, bigger, violating_timestamp)

        db_session.add(replayed_order)

        with pytest.raises(sa_exc.IntegrityError, match='ordered_timestamps'):
            db_session.commit()

    def test_timestamps_unordered_scheduled(self, db_session, make_replay_order):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        replayed_pre_order = make_replay_order(scheduled=True)
        # As we subtract 1 second in the generic case,
        # choose one second after a quarter of an hour.
        replayed_pre_order.placed_at = dt.datetime(*test_config.DATE, 11, 45, 1)
        self.test_timestamps_unordered(
            db_session, replayed_pre_order, 'placed_at < scheduled_delivery_at',
        )

    @pytest.mark.parametrize(
        'comparison',
        [
            'placed_at < cancelled_at',
            'restaurant_notified_at < cancelled_at',
            'restaurant_confirmed_at < cancelled_at',
            'restaurant_ready_at < cancelled_at',
            'dispatch_at < cancelled_at',
            'courier_notified_at < cancelled_at',
            'courier_accepted_at < cancelled_at',
            'reached_pickup_at < cancelled_at',
        ],
    )
    def test_timestamps_unordered_cancelled(
        self, db_session, replayed_order, comparison,
    ):
        """Insert an instance with invalid data.

        This is one of two special cases. See the generic case above.
        """
        replayed_order.pickup_at = None
        replayed_order.left_pickup_at = None
        replayed_order.reached_delivery_at = None
        replayed_order.delivery_at = None

        self.test_timestamps_unordered(db_session, replayed_order, comparison)


class TestProperties:
    """Test properties in `ReplayedOrder`.

    The `replayed_order` fixture uses the defaults specified in
    `factories.ReplayedOrderFactory` and provided by the `make_replay_order` fixture.
    """

    def test_has_customer(self, replayed_order):
        """Test `ReplayedOrder.customer` property."""
        result = replayed_order.customer

        assert result is replayed_order.actual.customer

    def test_has_restaurant(self, replayed_order):
        """Test `ReplayedOrder.restaurant` property."""
        result = replayed_order.restaurant

        assert result is replayed_order.actual.restaurant

    def test_has_pickup_address(self, replayed_order):
        """Test `ReplayedOrder.pickup_address` property."""
        result = replayed_order.pickup_address

        assert result is replayed_order.actual.pickup_address

    def test_has_delivery_address(self, replayed_order):
        """Test `ReplayedOrder.delivery_address` property."""
        result = replayed_order.delivery_address

        assert result is replayed_order.actual.delivery_address
