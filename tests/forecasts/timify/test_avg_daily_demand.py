"""Tests for the `OrderHistory.avg_daily_demand()` method."""

from tests import config as test_config


def test_avg_daily_demand_with_constant_demand(
    order_history, good_pixel_id, predict_at,
):
    """The average daily demand must be the number of time steps ...

    ... if the demand is `1` at each time step.

    Note: The `order_history` fixture assumes `12` time steps per day as it
    uses `LONG_TIME_STEP=60` as the length of a time step.
    """
    result = order_history.avg_daily_demand(
        pixel_id=good_pixel_id,
        predict_day=predict_at.date(),
        train_horizon=test_config.LONG_TRAIN_HORIZON,
    )

    assert result == 12.0


def test_avg_daily_demand_with_no_demand(
    order_history, good_pixel_id, predict_at,
):
    """Without demand, the average daily demand must be `0.0`."""
    order_history._data.loc[:, 'n_orders'] = 0

    result = order_history.avg_daily_demand(
        pixel_id=good_pixel_id,
        predict_day=predict_at.date(),
        train_horizon=test_config.LONG_TRAIN_HORIZON,
    )

    assert result == 0.0
