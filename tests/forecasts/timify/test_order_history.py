"""Test the basic functionalities in the `OrderHistory` class."""

import pytest

from tests import config as test_config
from urban_meal_delivery.forecasts import timify


@pytest.fixture
def order_history(grid):
    """An `OrderHistory` object."""
    return timify.OrderHistory(grid=grid, time_step=test_config.LONG_TIME_STEP)


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

    def test_totals_is_cached(self, order_history, monkeypatch):
        """Test `OrderHistory.totals` property.

        The result of the `OrderHistory.aggregate_orders()` method call
        is cached in the `OrderHistory.totals` property.
        """
        sentinel = object()
        monkeypatch.setattr(order_history, 'aggregate_orders', lambda: sentinel)

        result1 = order_history.totals
        result2 = order_history.totals

        assert result1 is result2
        assert result1 is sentinel
