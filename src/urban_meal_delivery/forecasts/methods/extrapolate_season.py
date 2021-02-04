"""Forecast by linear extrapolation of a seasonal component."""

import pandas as pd
from statsmodels.tsa import api as ts_stats


def predict(
    training_ts: pd.Series, forecast_interval: pd.DatetimeIndex, *, frequency: int,
) -> pd.DataFrame:
    """Extrapolate a seasonal component with a linear model.

    A naive forecast for each time unit of the day is calculated by linear
    extrapolation from all observations of the same time of day and on the same
    day of the week (i.e., same seasonal lag).

    Note: The function does not check if the `forecast_interval`
    extends the `training_ts`'s interval without a gap!

    Args:
        training_ts: past observations to be fitted;
            assumed to be a seasonal component after time series decomposition
        forecast_interval: interval into which the `training_ts` is forecast;
            its length becomes the numbers of time steps to be forecast
        frequency: frequency of the observations in the `training_ts`

    Returns:
        predictions: point forecasts (i.e., the "prediction" column);
            includes the four "low/high80/95" columns for the confidence intervals
            that only contain `NaN` values as this method does not make
            any statistical assumptions about the time series process

    Raises:
        ValueError: if `training_ts` contains `NaN` values or some predictions
            could not be made for time steps in the `forecast_interval`
    """
    if training_ts.isnull().any():
        raise ValueError('`training_ts` must not contain `NaN` values')

    extrapolated_ts = pd.Series(index=forecast_interval, dtype=float)
    seasonal_lag = frequency * (training_ts.index[1] - training_ts.index[0])

    for lag in range(frequency):
        # Obtain all `observations` of the same seasonal lag and
        # fit a straight line through them (= `trend`).
        observations = training_ts[slice(lag, 999_999_999, frequency)]
        trend = observations - ts_stats.detrend(observations)

        # Create a point forecast by linear extrapolation
        # for one or even more time steps ahead.
        slope = trend[-1] - trend[-2]
        prediction = trend[-1] + slope
        idx = observations.index.max() + seasonal_lag
        while idx <= forecast_interval.max():
            if idx in forecast_interval:
                extrapolated_ts.loc[idx] = prediction
            prediction += slope
            idx += seasonal_lag

    # Sanity check.
    if extrapolated_ts.isnull().any():  # pragma: no cover
        raise ValueError('missing predictions in the `forecast_interval`')

    return pd.DataFrame(
        data={
            'prediction': extrapolated_ts.round(5),
            'low80': float('NaN'),
            'high80': float('NaN'),
            'low95': float('NaN'),
            'high95': float('NaN'),
        },
        index=forecast_interval,
    )
