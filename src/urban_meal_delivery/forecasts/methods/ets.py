"""A wrapper around R's "ets" function."""

import pandas as pd
from rpy2 import robjects
from rpy2.robjects import pandas2ri


def predict(
    training_ts: pd.Series,
    forecast_interval: pd.DatetimeIndex,
    *,
    frequency: int,
    seasonal_fit: bool = False,
) -> pd.DataFrame:
    """Predict with an automatically calibrated ETS model.

    Note: The function does not check if the `forecast_interval`
    extends the `training_ts`'s interval without a gap!

    Args:
        training_ts: past observations to be fitted
        forecast_interval: interval into which the `training_ts` is forecast;
            its length becomes the step size `h` in the forecasting model in R
        frequency: frequency of the observations in the `training_ts`
        seasonal_fit: if a "ZZZ" (seasonal) or a "ZZN" (non-seasonal)
            type ETS model should be fitted

    Returns:
        predictions: point forecasts (i.e., the "prediction" column) and
            confidence intervals (i.e, the four "low/high80/95" columns)

    Raises:
        ValueError: if `training_ts` contains `NaN` values
    """
    # Initialize R only if necessary as it is tested only in nox's
    # "ci-tests-slow" session and "ci-tests-fast" should not fail.
    from urban_meal_delivery import init_r  # noqa:F401,WPS433

    # Re-seed R every time it is used to ensure reproducibility.
    robjects.r('set.seed(42)')

    if training_ts.isnull().any():
        raise ValueError('`training_ts` must not contain `NaN` values')

    # Copy the data from Python to R.
    robjects.globalenv['data'] = robjects.r['ts'](
        pandas2ri.py2rpy(training_ts), frequency=frequency,
    )

    model = 'ZZZ' if bool(seasonal_fit) else 'ZZN'
    n_steps_ahead = len(forecast_interval)

    # Make the predictions in R.
    result = robjects.r(
        f"""
        as.data.frame(
            forecast(
                ets(data, model = "{model:s}"),
                h = {n_steps_ahead:d}
            )
        )
        """,
    )

    # Convert the results into a nice `pd.DataFrame` with the right `.index`.
    forecasts = pandas2ri.rpy2py(result)
    forecasts.index = forecast_interval

    return forecasts.round(5).rename(
        columns={
            'Point Forecast': 'prediction',
            'Lo 80': 'low80',
            'Hi 80': 'high80',
            'Lo 95': 'low95',
            'Hi 95': 'high95',
        },
    )
