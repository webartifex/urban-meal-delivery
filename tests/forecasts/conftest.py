"""Fixtures and globals for testing `urban_meal_delivery.forecasts`."""

import datetime as dt

import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import config


# See remarks in `vertical_datetime_index` fixture.
VERTICAL_FREQUENCY = 7 * 12

# The default `ns` suggested for the STL method.
NS = 7


@pytest.fixture
def horizontal_datetime_index():
    """A `pd.Index` with `DateTime` values.

    The times resemble a horizontal time series with a `frequency` of `7`.
    All observations take place at `NOON`.
    """
    first_start_at = dt.datetime(
        test_config.YEAR, test_config.MONTH, test_config.DAY, test_config.NOON, 0,
    )

    gen = (
        start_at
        for start_at in pd.date_range(first_start_at, test_config.END, freq='D')
    )

    index = pd.Index(gen)
    index.name = 'start_at'

    assert len(index) == 15  # sanity check

    return index


@pytest.fixture
def horizontal_no_demand(horizontal_datetime_index):
    """A horizontal time series of order totals when there was no demand."""
    return pd.Series(0, index=horizontal_datetime_index, name='order_totals')


@pytest.fixture
def vertical_datetime_index():
    """A `pd.Index` with `DateTime` values.

    The times resemble a vertical time series with a
    `frequency` of `7` times the number of daily time steps,
    which is `12` for `LONG_TIME_STEP` values.
    """
    gen = (
        start_at
        for start_at in pd.date_range(
            test_config.START, test_config.END, freq=f'{test_config.LONG_TIME_STEP}T',
        )
        if config.SERVICE_START <= start_at.hour < config.SERVICE_END
    )

    index = pd.Index(gen)
    index.name = 'start_at'

    assert len(index) == 15 * 12  # sanity check

    return index


@pytest.fixture
def vertical_no_demand(vertical_datetime_index):
    """A vertical time series of order totals when there was no demand."""
    return pd.Series(0, index=vertical_datetime_index, name='order_totals')
