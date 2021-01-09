"""Test the basic functionalities in the `OrderHistory` class."""
# pylint:disable=no-self-use

import pytest

from tests import config as test_config
from urban_meal_delivery.forecasts import timify


class TestSpecialMethods:
    """Test the special methods in `OrderHistory`."""

    @pytest.mark.parametrize('time_step', test_config.TIME_STEPS)
    def test_instantiate(self, grid, time_step):
        """Test `OrderHistory.__init__()`."""
        oh = timify.OrderHistory(grid=grid, time_step=time_step)

        assert oh is not None


class TestProperties:
    """Test the properties in `OrderHistory`."""

    def test_totals_is_cached(self, grid, monkeypatch):
        """Test `.totals` property.

        The result of the `OrderHistory.aggregate_orders()` method call
        is cached in the `OrderHistory.totals` property.
        """
        oh = timify.OrderHistory(grid=grid, time_step=test_config.LONG_TIME_STEP)

        sentinel = object()
        monkeypatch.setattr(oh, 'aggregate_orders', lambda: sentinel)

        result1 = oh.totals
        result2 = oh.totals

        assert result1 is result2
        assert result1 is sentinel
