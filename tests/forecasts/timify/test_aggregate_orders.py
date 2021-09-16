"""Test the `OrderHistory.aggregate_orders()` method."""

import datetime

import pytest

from tests import config as test_config
from urban_meal_delivery import db
from urban_meal_delivery.forecasts import timify


@pytest.mark.db
class TestAggregateOrders:
    """Test the `OrderHistory.aggregate_orders()` method.

    The test cases are integration tests that model realistic scenarios.
    """

    @pytest.fixture
    def addresses_mock(self, mocker, monkeypatch):
        """A `Mock` whose `.return_value` are to be set ...

        ... to the addresses that are gridified. The addresses are
        all considered `Order.pickup_address` attributes for some orders.

        Note: This fixture also exists in `tests.db.test_grids`.
        """
        mock = mocker.Mock()
        query = (  # noqa:ECE001
            mock.query.return_value.join.return_value.filter.return_value.all  # noqa:E501,WPS219
        )
        monkeypatch.setattr(db, 'session', mock)

        return query

    @pytest.fixture
    def one_pixel_grid(self, db_session, city, restaurant, addresses_mock):
        """A persisted `Grid` with one `Pixel`.

        `restaurant` must be a dependency as otherwise the `restaurant.address`
        is not put into the database as an `Order.pickup_address`.
        """
        addresses_mock.return_value = [restaurant.address]

        # `+1` as otherwise there would be a second pixel in one direction.
        side_length = max(city.total_x, city.total_y) + 1
        grid = db.Grid.gridify(city=city, side_length=side_length)
        db_session.add(grid)

        assert len(grid.pixels) == 1  # sanity check

        return grid

    def test_no_orders(self, db_session, one_pixel_grid, restaurant):
        """Edge case that does not occur for real-life data."""
        db_session.commit()
        assert len(restaurant.orders) == 0  # noqa:WPS507  sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        assert len(result) == 0  # noqa:WPS507

    def test_evenly_distributed_ad_hoc_orders(
        self, db_session, one_pixel_grid, restaurant, make_order,
    ):
        """12 ad-hoc orders, one per operating hour."""
        # Create one order per hour and 12 orders in total.
        for hour in range(11, 23):
            order = make_order(
                scheduled=False,
                restaurant=restaurant,
                placed_at=datetime.datetime(*test_config.DATE, hour, 11),
            )
            db_session.add(order)

        db_session.commit()

        assert len(restaurant.orders) == 12  # sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # The resulting `DataFrame` has 12 rows holding `1`s.
        assert len(result) == 12
        assert result['n_orders'].min() == 1
        assert result['n_orders'].max() == 1
        assert result['n_orders'].sum() == 12

    def test_evenly_distributed_ad_hoc_orders_with_no_demand_late(  # noqa:WPS218
        self, db_session, one_pixel_grid, restaurant, make_order,
    ):
        """10 ad-hoc orders, one per hour, no orders after 21."""
        # Create one order per hour and 10 orders in total.
        for hour in range(11, 21):
            order = make_order(
                scheduled=False,
                restaurant=restaurant,
                placed_at=datetime.datetime(*test_config.DATE, hour, 11),
            )
            db_session.add(order)

        db_session.commit()

        assert len(restaurant.orders) == 10  # sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # Even though there are only 10 orders, there are 12 rows in the `DataFrame`.
        # That is so as `0`s are filled in for hours without any demand at the end.
        assert len(result) == 12
        assert result['n_orders'].min() == 0
        assert result['n_orders'].max() == 1
        assert result.iloc[:10]['n_orders'].sum() == 10
        assert result.iloc[10:]['n_orders'].sum() == 0

    def test_one_ad_hoc_order_every_other_hour(
        self, db_session, one_pixel_grid, restaurant, make_order,
    ):
        """6 ad-hoc orders, one every other hour."""
        # Create one order every other hour.
        for hour in range(11, 23, 2):
            order = make_order(
                scheduled=False,
                restaurant=restaurant,
                placed_at=datetime.datetime(*test_config.DATE, hour, 11),
            )
            db_session.add(order)

        db_session.commit()

        assert len(restaurant.orders) == 6  # sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # The resulting `DataFrame` has 12 rows, 6 holding `0`s, and 6 holding `1`s.
        assert len(result) == 12
        assert result['n_orders'].min() == 0
        assert result['n_orders'].max() == 1
        assert result['n_orders'].sum() == 6

    def test_one_ad_hoc_and_one_pre_order(
        self, db_session, one_pixel_grid, restaurant, make_order,
    ):
        """1 ad-hoc and 1 scheduled order.

        The scheduled order is discarded.
        """
        ad_hoc_order = make_order(
            scheduled=False,
            restaurant=restaurant,
            placed_at=datetime.datetime(*test_config.DATE, 11, 11),
        )
        db_session.add(ad_hoc_order)

        pre_order = make_order(
            scheduled=True,
            restaurant=restaurant,
            placed_at=datetime.datetime(*test_config.DATE, 9, 0),
            scheduled_delivery_at=datetime.datetime(*test_config.DATE, 12, 0),
        )
        db_session.add(pre_order)

        db_session.commit()

        assert len(restaurant.orders) == 2  # sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # The resulting `DataFrame` has 12 rows, 11 holding `0`s, and one holding a `1`.
        assert len(result) == 12
        assert result['n_orders'].min() == 0
        assert result['n_orders'].max() == 1
        assert result['n_orders'].sum() == 1

    def test_evenly_distributed_ad_hoc_orders_with_half_hour_time_steps(  # noqa:WPS218
        self, db_session, one_pixel_grid, restaurant, make_order,
    ):
        """12 ad-hoc orders, one per hour, with 30 minute time windows.

        In half the time steps, there is no demand.
        """
        # Create one order per hour and 10 orders in total.
        for hour in range(11, 23):
            order = make_order(
                scheduled=False,
                restaurant=restaurant,
                placed_at=datetime.datetime(*test_config.DATE, hour, 11),
            )
            db_session.add(order)

        db_session.commit()

        assert len(restaurant.orders) == 12  # sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.SHORT_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # The resulting `DataFrame` has 24 rows for the 24 30-minute time steps.
        # The rows' values are `0` and `1` alternating.
        assert len(result) == 24
        assert result['n_orders'].min() == 0
        assert result['n_orders'].max() == 1
        assert result.iloc[::2]['n_orders'].sum() == 12
        assert result.iloc[1::2]['n_orders'].sum() == 0

    def test_ad_hoc_orders_over_two_days(
        self, db_session, one_pixel_grid, restaurant, make_order,
    ):
        """First day 12 ad-hoc orders, one per operating hour ...

        ... and 6 orders, one every other hour on the second day.
        In total, there are 18 orders.
        """
        # Create one order per hour and 12 orders in total.
        for hour in range(11, 23):
            order = make_order(
                scheduled=False,
                restaurant=restaurant,
                placed_at=datetime.datetime(*test_config.DATE, hour, 11),
            )
            db_session.add(order)

        # Create one order every other hour and 6 orders in total.
        for hour in range(11, 23, 2):  # noqa:WPS440
            order = make_order(
                scheduled=False,
                restaurant=restaurant,
                placed_at=datetime.datetime(
                    test_config.YEAR,
                    test_config.MONTH,
                    test_config.DAY + 1,
                    hour,  # noqa:WPS441
                    11,
                ),
            )
            db_session.add(order)

        db_session.commit()

        assert len(restaurant.orders) == 18  # sanity check

        oh = timify.OrderHistory(
            grid=one_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # The resulting `DataFrame` has 24 rows, 12 for each day.
        assert len(result) == 24
        assert result['n_orders'].min() == 0
        assert result['n_orders'].max() == 1
        assert result['n_orders'].sum() == 18

    @pytest.fixture
    def two_pixel_grid(  # noqa:WPS211
        self, db_session, city, make_address, make_restaurant, addresses_mock,
    ):
        """A persisted `Grid` with two `Pixel` objects."""
        # One `Address` in the lower-left `Pixel`, ...
        address1 = make_address(latitude=48.8357377, longitude=2.2517412)
        # ... and another one in the upper-right one.
        address2 = make_address(latitude=48.8898312, longitude=2.4357622)

        addresses_mock.return_value = [address1, address2]

        # Create `Restaurant`s at the two addresses.
        make_restaurant(address=address1)
        make_restaurant(address=address2)

        # This creates four `Pixel`s, two of which have no `pickup_address`.
        side_length = max(city.total_x // 2, city.total_y // 2) + 1

        grid = db.Grid.gridify(city=city, side_length=side_length)

        db_session.add(grid)

        assert len(grid.pixels) == 2  # sanity check

        return grid

    def test_two_pixels_with_shifted_orders(  # noqa:WPS218
        self, db_session, two_pixel_grid, make_order,
    ):
        """One restaurant with one order every other hour ...

        ... and another restaurant with two orders per hour.
        In total, there are 30 orders.
        """
        address1, address2 = two_pixel_grid.city.addresses
        # Rarely, an `Address` may have several `Restaurant`s in the real dataset.
        restaurant1, restaurant2 = address1.restaurants[0], address2.restaurants[0]

        # Create one order every other hour for `restaurant1`.
        for hour in range(11, 23, 2):
            order = make_order(
                scheduled=False,
                restaurant=restaurant1,
                placed_at=datetime.datetime(*test_config.DATE, hour, 11),
            )
            db_session.add(order)

        # Create two orders per hour for `restaurant2`.
        for hour in range(11, 23):  # noqa:WPS440
            order = make_order(
                scheduled=False,
                restaurant=restaurant2,
                placed_at=datetime.datetime(
                    test_config.YEAR,
                    test_config.MONTH,
                    test_config.DAY,
                    hour,  # noqa:WPS441
                    13,
                ),
            )
            db_session.add(order)

            order = make_order(
                scheduled=False,
                restaurant=restaurant2,
                placed_at=datetime.datetime(
                    test_config.YEAR,
                    test_config.MONTH,
                    test_config.DAY,
                    hour,  # noqa:WPS441
                    14,
                ),
            )
            db_session.add(order)

        db_session.commit()

        # sanity checks
        assert len(restaurant1.orders) == 6
        assert len(restaurant2.orders) == 24

        oh = timify.OrderHistory(
            grid=two_pixel_grid, time_step=test_config.LONG_TIME_STEP,
        )

        result = oh.aggregate_orders()

        # The resulting `DataFrame` has 24 rows, 12 for each pixel.
        assert len(result) == 24
        assert result['n_orders'].min() == 0
        assert result['n_orders'].max() == 2
        assert result['n_orders'].sum() == 30
