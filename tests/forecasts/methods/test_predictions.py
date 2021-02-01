"""Test all the `*.predict()` functions in the `methods` sub-package."""

import datetime as dt

import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import config
from urban_meal_delivery.forecasts.methods import arima
from urban_meal_delivery.forecasts.methods import ets
from urban_meal_delivery.forecasts.methods import extrapolate_season


@pytest.fixture
def forecast_interval():
    """A `pd.Index` with `DateTime` values ...

    ... that takes place one day after the `START`-`END` horizon and
    resembles an entire day (`12` "start_at" values as we use `LONG_TIME_STEP`).
    """
    future_day = test_config.END.date() + dt.timedelta(days=1)
    first_start_at = dt.datetime(
        future_day.year, future_day.month, future_day.day, config.SERVICE_START, 0,
    )
    end_of_day = dt.datetime(
        future_day.year, future_day.month, future_day.day, config.SERVICE_END, 0,
    )

    gen = (
        start_at
        for start_at in pd.date_range(
            first_start_at, end_of_day, freq=f'{test_config.LONG_TIME_STEP}T',
        )
        if config.SERVICE_START <= start_at.hour < config.SERVICE_END
    )

    index = pd.Index(gen)
    index.name = 'start_at'

    return index


@pytest.fixture
def forecast_time_step():
    """A `pd.Index` with one `DateTime` value, resembling `NOON`."""
    future_day = test_config.END.date() + dt.timedelta(days=1)

    start_at = dt.datetime(
        future_day.year, future_day.month, future_day.day, test_config.NOON, 0,
    )

    index = pd.Index([start_at])
    index.name = 'start_at'

    return index


@pytest.mark.r
@pytest.mark.parametrize(
    'func', [arima.predict, ets.predict, extrapolate_season.predict],
)
class TestMakePredictions:
    """Make predictions with `arima.predict()` and `ets.predict()`."""

    def test_training_data_contains_nan_values(
        self, func, vertical_no_demand, forecast_interval,
    ):
        """`training_ts` must not contain `NaN` values."""
        vertical_no_demand.iloc[0] = pd.NA

        with pytest.raises(ValueError, match='must not contain `NaN`'):
            func(
                training_ts=vertical_no_demand,
                forecast_interval=forecast_interval,
                frequency=test_config.VERTICAL_FREQUENCY_LONG,
            )

    def test_structure_of_returned_dataframe(
        self, func, vertical_no_demand, forecast_interval,
    ):
        """Both `.predict()` return a `pd.DataFrame` with five columns."""
        result = func(
            training_ts=vertical_no_demand,
            forecast_interval=forecast_interval,
            frequency=test_config.VERTICAL_FREQUENCY_LONG,
        )

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == [
            'prediction',
            'low80',
            'high80',
            'low95',
            'high95',
        ]

    def test_predict_horizontal_time_series_with_no_demand(
        self, func, horizontal_no_demand, forecast_time_step,
    ):
        """Predicting a horizontal time series with no demand ...

        ... returns a `pd.DataFrame` with five columns holding only `0.0` values.
        """
        predictions = func(
            training_ts=horizontal_no_demand,
            forecast_interval=forecast_time_step,
            frequency=7,
        )

        result = predictions.sum().sum()

        assert result == 0

    def test_predict_vertical_time_series_with_no_demand(
        self, func, vertical_no_demand, forecast_interval,
    ):
        """Predicting a vertical time series with no demand ...

        ... returns a `pd.DataFrame` with five columns holding only `0.0` values.
        """
        predictions = func(
            training_ts=vertical_no_demand,
            forecast_interval=forecast_interval,
            frequency=test_config.VERTICAL_FREQUENCY_LONG,
        )

        result = predictions.sum().sum()

        assert result == 0
