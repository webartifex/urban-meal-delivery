"""Test the basic functionalities in the `OrderHistory` class."""

import datetime as dt

import pytest

from tests import config as test_config
from urban_meal_delivery.forecasts import timify


class TestSpecialMethods:
    """Test the special methods in `OrderHistory`."""

    def test_instantiate(self, order_history):
        """Test `OrderHistory.__init__()`."""
        assert order_history is not None


class TestProperties:
    """Test the properties in `OrderHistory`."""

    @pytest.mark.parametrize('time_step', test_config.TIME_STEPS)
    def test_time_step(self, grid, time_step):
        """Test `OrderHistory.time_step` property."""
        order_history = timify.OrderHistory(grid=grid, time_step=time_step)

        result = order_history.time_step

        assert result == time_step

    def test_totals(self, order_history, order_totals):
        """Test `OrderHistory.totals` property.

        The result of the `OrderHistory.aggregate_orders()` method call
        is cached in the `OrderHistory.totals` property.

        Note: `OrderHistory.aggregate_orders()` is not called as
        `OrderHistory._data` is already set in the `order_history` fixture.
        """
        result = order_history.totals

        assert result is order_totals

    def test_totals_is_cached(self, order_history, monkeypatch):
        """Test `OrderHistory.totals` property.

        The result of the `OrderHistory.aggregate_orders()` method call
        is cached in the `OrderHistory.totals` property.

        Note: We make `OrderHistory.aggregate_orders()` return a `sentinel`
        that is cached into `OrderHistory._data`, which must be unset first.
        """
        monkeypatch.setattr(order_history, '_data', None)
        sentinel = object()
        monkeypatch.setattr(order_history, 'aggregate_orders', lambda: sentinel)

        result1 = order_history.totals
        result2 = order_history.totals

        assert result1 is result2
        assert result1 is sentinel


class TestMethods:
    """Test various methods in `OrderHistory`."""

    def test_first_order_at_existing_pixel(self, order_history, good_pixel_id):
        """Test `OrderHistory.first_order_at()` with good input."""
        result = order_history.first_order_at(good_pixel_id)

        assert result == test_config.START

    def test_first_order_at_non_existing_pixel(self, order_history, good_pixel_id):
        """Test `OrderHistory.first_order_at()` with bad input."""
        with pytest.raises(
            LookupError, match='`pixel_id` is not in the `grid`',
        ):
            order_history.first_order_at(-1)

    def test_last_order_at_existing_pixel(self, order_history, good_pixel_id):
        """Test `OrderHistory.last_order_at()` with good input."""
        result = order_history.last_order_at(good_pixel_id)

        one_time_step = dt.timedelta(minutes=test_config.LONG_TIME_STEP)
        assert result == test_config.END - one_time_step

    def test_last_order_at_non_existing_pixel(self, order_history, good_pixel_id):
        """Test `OrderHistory.last_order_at()` with bad input."""
        with pytest.raises(
            LookupError, match='`pixel_id` is not in the `grid`',
        ):
            order_history.last_order_at(-1)
