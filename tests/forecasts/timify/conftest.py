"""Fixture for testing the `urban_meal_delivery.forecast.timify` module."""

import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import config
from urban_meal_delivery.forecasts import timify


@pytest.fixture
def good_pixel_id(pixel):
    """A `pixel_id` that is on the `grid`."""
    return pixel.id  # `== 1`


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

    # Sanity check: n_pixels * n_time_steps_per_day * n_weekdays * n_weeks.
    assert len(df) == 2 * 12 * (7 * 2 + 1)

    return df


@pytest.fixture
def order_history(order_totals, grid):
    """An `OrderHistory` object that does not need the database.

    Uses the LONG_TIME_STEP as the length of a time step.
    """
    oh = timify.OrderHistory(grid=grid, time_step=test_config.LONG_TIME_STEP)
    oh._data = order_totals

    return oh
