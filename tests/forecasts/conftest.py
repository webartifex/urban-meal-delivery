"""Fixtures for testing the `urban_meal_delivery.forecasts` sub-package."""

import datetime as dt

import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import config
from urban_meal_delivery.forecasts import timify


@pytest.fixture
def horizontal_datetime_index():
    """A `pd.Index` with `DateTime` values.

    The times resemble a horizontal time series with a `frequency` of `7`.
    All observations take place at `NOON`.
    """
    first_start_at = dt.datetime(*test_config.DATE, test_config.NOON, 0)

    gen = (
        start_at
        for start_at in pd.date_range(first_start_at, test_config.END, freq='D')
    )

    index = pd.Index(gen)
    index.name = 'start_at'

    # Sanity check.
    # `+1` as both the `START` and `END` day are included.
    n_days = (test_config.END - test_config.START).days + 1
    assert len(index) == n_days

    return index


@pytest.fixture
def horizontal_no_demand(horizontal_datetime_index):
    """A horizontal time series with order totals: no demand."""
    return pd.Series(0, index=horizontal_datetime_index, name='n_orders')


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

    # Sanity check: n_days * n_number_of_opening_hours.
    # `+1` as both the `START` and `END` day are included.
    n_days = (test_config.END - test_config.START).days + 1
    assert len(index) == n_days * 12

    return index


@pytest.fixture
def vertical_no_demand(vertical_datetime_index):
    """A vertical time series with order totals: no demand."""
    return pd.Series(0, index=vertical_datetime_index, name='n_orders')


@pytest.fixture
def good_pixel_id(pixel):
    """A `pixel_id` that is on the `grid`."""
    return pixel.id  # `== 1`


@pytest.fixture
def predict_at() -> dt.datetime:
    """`NOON` on the day to be predicted."""
    return dt.datetime(
        test_config.END.year,
        test_config.END.month,
        test_config.END.day,
        test_config.NOON,
    )


@pytest.fixture
def order_totals(good_pixel_id):
    """A mock for `OrderHistory.totals`.

    To be a bit more realistic, we sample two pixels on the `grid`.

    Uses the LONG_TIME_STEP as the length of a time step.
    """
    pixel_ids = [good_pixel_id, good_pixel_id + 1]

    gen = (
        (pixel_id, start_at)
        for pixel_id in pixel_ids
        for start_at in pd.date_range(
            test_config.START, test_config.END, freq=f'{test_config.LONG_TIME_STEP}T',
        )
        if config.SERVICE_START <= start_at.hour < config.SERVICE_END
    )

    # Re-index `data` filling in `0`s where there is no demand.
    index = pd.MultiIndex.from_tuples(gen)
    index.names = ['pixel_id', 'start_at']

    df = pd.DataFrame(data={'n_orders': 1}, index=index)

    # Sanity check: n_pixels * n_time_steps_per_day * n_days.
    # `+1` as both the `START` and `END` day are included.
    n_days = (test_config.END - test_config.START).days + 1
    assert len(df) == 2 * 12 * n_days

    return df


@pytest.fixture
def order_history(order_totals, grid):
    """An `OrderHistory` object that does not need the database.

    Uses the LONG_TIME_STEP as the length of a time step.
    """
    oh = timify.OrderHistory(grid=grid, time_step=test_config.LONG_TIME_STEP)
    oh._data = order_totals

    return oh
