"""Test the code generating time series with the order totals.

Unless otherwise noted, each `time_step` is 60 minutes long implying
12 time steps per day (i.e., we use `LONG_TIME_STEP` by default).
"""

import datetime

import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import config


@pytest.fixture
def good_predict_at():
    """A `predict_at` within `START`-`END` and ...

    ... a long enough history so that either `SHORT_TRAIN_HORIZON`
    or `LONG_TRAIN_HORIZON` works.
    """
    return datetime.datetime(
        test_config.END.year,
        test_config.END.month,
        test_config.END.day,
        test_config.NOON,
        0,
    )


@pytest.fixture
def bad_predict_at():
    """A `predict_at` within `START`-`END` but ...

    ... not a long enough history so that both `SHORT_TRAIN_HORIZON`
    and `LONG_TRAIN_HORIZON` do not work.
    """
    predict_day = test_config.END - datetime.timedelta(weeks=6, days=1)
    return datetime.datetime(
        predict_day.year, predict_day.month, predict_day.day, test_config.NOON, 0,
    )


class TestMakeHorizontalTimeSeries:
    """Test the `OrderHistory.make_horizontal_ts()` method."""

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_wrong_pixel(self, order_history, good_predict_at, train_horizon):
        """A `pixel_id` that is not in the `grid`."""
        with pytest.raises(LookupError):
            order_history.make_horizontal_ts(
                pixel_id=999_999,
                predict_at=good_predict_at,
                train_horizon=train_horizon,
            )

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_are_series(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The time series come as a `pd.Series`."""
        result = order_history.make_horizontal_ts(
            pixel_id=good_pixel_id,
            predict_at=good_predict_at,
            train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        assert isinstance(training_ts, pd.Series)
        assert training_ts.name == 'n_orders'
        assert isinstance(actuals_ts, pd.Series)
        assert actuals_ts.name == 'n_orders'

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_have_correct_length(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The length of a training time series must be a multiple of `7` ...

        ... whereas the time series with the actual order counts has only `1` value.
        """
        result = order_history.make_horizontal_ts(
            pixel_id=good_pixel_id,
            predict_at=good_predict_at,
            train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        assert len(training_ts) == 7 * train_horizon
        assert len(actuals_ts) == 1

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_frequency_is_number_of_weekdays(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The `frequency` must be `7`."""
        result = order_history.make_horizontal_ts(
            pixel_id=good_pixel_id,
            predict_at=good_predict_at,
            train_horizon=train_horizon,
        )

        _, frequency, _ = result  # noqa:WPS434

        assert frequency == 7

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_no_long_enough_history1(
        self, order_history, good_pixel_id, bad_predict_at, train_horizon,
    ):
        """If the `predict_at` day is too early in the `START`-`END` horizon ...

        ... the history of order totals is not long enough.
        """
        with pytest.raises(RuntimeError):
            order_history.make_horizontal_ts(
                pixel_id=good_pixel_id,
                predict_at=bad_predict_at,
                train_horizon=train_horizon,
            )

    def test_no_long_enough_history2(
        self, order_history, good_pixel_id, good_predict_at,
    ):
        """If the `train_horizon` is longer than the `START`-`END` horizon ...

        ... the history of order totals can never be long enough.
        """
        with pytest.raises(RuntimeError):
            order_history.make_horizontal_ts(
                pixel_id=good_pixel_id, predict_at=good_predict_at, train_horizon=999,
            )


class TestMakeVerticalTimeSeries:
    """Test the `OrderHistory.make_vertical_ts()` method."""

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_wrong_pixel(self, order_history, good_predict_at, train_horizon):
        """A `pixel_id` that is not in the `grid`."""
        with pytest.raises(LookupError):
            order_history.make_vertical_ts(
                pixel_id=999_999,
                predict_day=good_predict_at.date(),
                train_horizon=train_horizon,
            )

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_are_series(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The time series come as `pd.Series`."""
        result = order_history.make_vertical_ts(
            pixel_id=good_pixel_id,
            predict_day=good_predict_at.date(),
            train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        assert isinstance(training_ts, pd.Series)
        assert training_ts.name == 'n_orders'
        assert isinstance(actuals_ts, pd.Series)
        assert actuals_ts.name == 'n_orders'

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_have_correct_length(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The length of a training time series is the product of the ...

        ... weekly time steps (i.e., product of `7` and the number of daily time steps)
        and the `train_horizon` in weeks.

        The time series with the actual order counts always holds one observation
        per time step of a day.
        """
        result = order_history.make_vertical_ts(
            pixel_id=good_pixel_id,
            predict_day=good_predict_at.date(),
            train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        n_daily_time_steps = (
            60
            * (config.SERVICE_END - config.SERVICE_START)
            // test_config.LONG_TIME_STEP
        )

        assert len(training_ts) == 7 * n_daily_time_steps * train_horizon
        assert len(actuals_ts) == n_daily_time_steps

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_frequency_is_number_number_of_weekly_time_steps(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The `frequency` is the number of weekly time steps."""
        result = order_history.make_vertical_ts(
            pixel_id=good_pixel_id,
            predict_day=good_predict_at.date(),
            train_horizon=train_horizon,
        )

        _, frequency, _ = result  # noqa:WPS434

        n_daily_time_steps = (
            60
            * (config.SERVICE_END - config.SERVICE_START)
            // test_config.LONG_TIME_STEP
        )

        assert frequency == 7 * n_daily_time_steps

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_no_long_enough_history1(
        self, order_history, good_pixel_id, bad_predict_at, train_horizon,
    ):
        """If the `predict_at` day is too early in the `START`-`END` horizon ...

        ... the history of order totals is not long enough.
        """
        with pytest.raises(RuntimeError):
            order_history.make_vertical_ts(
                pixel_id=good_pixel_id,
                predict_day=bad_predict_at.date(),
                train_horizon=train_horizon,
            )

    def test_no_long_enough_history2(
        self, order_history, good_pixel_id, good_predict_at,
    ):
        """If the `train_horizon` is longer than the `START`-`END` horizon ...

        ... the history of order totals can never be long enough.
        """
        with pytest.raises(RuntimeError):
            order_history.make_vertical_ts(
                pixel_id=good_pixel_id,
                predict_day=good_predict_at.date(),
                train_horizon=999,
            )


class TestMakeRealTimeTimeSeries:
    """Test the `OrderHistory.make_realtime_ts()` method."""

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_wrong_pixel(self, order_history, good_predict_at, train_horizon):
        """A `pixel_id` that is not in the `grid`."""
        with pytest.raises(LookupError):
            order_history.make_realtime_ts(
                pixel_id=999_999,
                predict_at=good_predict_at,
                train_horizon=train_horizon,
            )

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_are_series(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The time series come as `pd.Series`."""
        result = order_history.make_realtime_ts(
            pixel_id=good_pixel_id,
            predict_at=good_predict_at,
            train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        assert isinstance(training_ts, pd.Series)
        assert training_ts.name == 'n_orders'
        assert isinstance(actuals_ts, pd.Series)
        assert actuals_ts.name == 'n_orders'

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_have_correct_length1(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The length of a training time series is the product of the ...

        ... weekly time steps (i.e., product of `7` and the number of daily time steps)
        and the `train_horizon` in weeks; however, this assertion only holds if
        we predict the first `time_step` of the day.

        The time series with the actual order counts always holds `1` value.
        """
        predict_at = datetime.datetime(
            good_predict_at.year,
            good_predict_at.month,
            good_predict_at.day,
            config.SERVICE_START,
            0,
        )
        result = order_history.make_realtime_ts(
            pixel_id=good_pixel_id, predict_at=predict_at, train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        n_daily_time_steps = (
            60
            * (config.SERVICE_END - config.SERVICE_START)
            // test_config.LONG_TIME_STEP
        )

        assert len(training_ts) == 7 * n_daily_time_steps * train_horizon
        assert len(actuals_ts) == 1

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_time_series_have_correct_length2(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The length of a training time series is the product of the ...

        ... weekly time steps (i.e., product of `7` and the number of daily time steps)
        and the `train_horizon` in weeks; however, this assertion only holds if
        we predict the first `time_step` of the day. Predicting any other `time_step`
        means that the training time series becomes longer by the number of time steps
        before the one being predicted.

        The time series with the actual order counts always holds `1` value.
        """
        assert good_predict_at.hour == test_config.NOON

        result = order_history.make_realtime_ts(
            pixel_id=good_pixel_id,
            predict_at=good_predict_at,
            train_horizon=train_horizon,
        )

        training_ts, _, actuals_ts = result

        n_daily_time_steps = (
            60
            * (config.SERVICE_END - config.SERVICE_START)
            // test_config.LONG_TIME_STEP
        )
        n_time_steps_before = (
            60 * (test_config.NOON - config.SERVICE_START) // test_config.LONG_TIME_STEP
        )

        assert (
            len(training_ts)
            == 7 * n_daily_time_steps * train_horizon + n_time_steps_before
        )
        assert len(actuals_ts) == 1

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_frequency_is_number_number_of_weekly_time_steps(
        self, order_history, good_pixel_id, good_predict_at, train_horizon,
    ):
        """The `frequency` is the number of weekly time steps."""
        result = order_history.make_realtime_ts(
            pixel_id=good_pixel_id,
            predict_at=good_predict_at,
            train_horizon=train_horizon,
        )

        _, frequency, _ = result  # noqa:WPS434

        n_daily_time_steps = (
            60
            * (config.SERVICE_END - config.SERVICE_START)
            // test_config.LONG_TIME_STEP
        )

        assert frequency == 7 * n_daily_time_steps

    @pytest.mark.parametrize('train_horizon', test_config.TRAIN_HORIZONS)
    def test_no_long_enough_history1(
        self, order_history, good_pixel_id, bad_predict_at, train_horizon,
    ):
        """If the `predict_at` day is too early in the `START`-`END` horizon ...

        ... the history of order totals is not long enough.
        """
        with pytest.raises(RuntimeError):
            order_history.make_realtime_ts(
                pixel_id=good_pixel_id,
                predict_at=bad_predict_at,
                train_horizon=train_horizon,
            )

    def test_no_long_enough_history2(
        self, order_history, good_pixel_id, good_predict_at,
    ):
        """If the `train_horizon` is longer than the `START`-`END` horizon ...

        ... the history of order totals can never be long enough.
        """
        with pytest.raises(RuntimeError):
            order_history.make_realtime_ts(
                pixel_id=good_pixel_id, predict_at=good_predict_at, train_horizon=999,
            )
