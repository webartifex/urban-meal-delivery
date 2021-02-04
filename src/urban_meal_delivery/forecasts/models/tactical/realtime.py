"""Real-time forecasting `*Model`s to predict demand for tactical purposes.

Real-time `*Model`s take order counts of all time steps in the training data
and make a prediction for only one time step on the day to be predicted (i.e.,
the one starting at `predict_at`). Thus, the training time series have a
`frequency` of the number of weekdays, `7`, times the number of time steps on a
day. For example, for 60-minute time steps, the `frequency` becomes `7 * 12`
(= operating hours from 11 am to 11 pm), which is `84`. Real-time `*Model`s
train the forecasting `methods` on a seasonally decomposed time series internally.
"""  # noqa:RST215

import datetime as dt

import pandas as pd

from urban_meal_delivery import db
from urban_meal_delivery.forecasts import methods
from urban_meal_delivery.forecasts.models import base


class RealtimeARIMAModel(base.ForecastingModelABC):
    """The ARIMA model applied on a real-time time series."""

    name = 'rtarima'

    def predict(
        self, pixel: db.Pixel, predict_at: dt.datetime, train_horizon: int,
    ) -> pd.DataFrame:
        """Predict demand for a time step.

        Args:
            pixel: pixel in which the prediction is made
            predict_at: time step (i.e., "start_at") to make the prediction for
            train_horizon: weeks of historic data used to predict `predict_at`

        Returns:
            actual order counts (i.e., the "actual" column),
                point forecasts (i.e., the "prediction" column), and
                confidence intervals (i.e, the four "low/high/80/95" columns);
                contains one row for the `predict_at` time step

        # noqa:DAR401 RuntimeError
        """
        # Generate the historic (and real-time) order time series.
        training_ts, frequency, actuals_ts = self._order_history.make_realtime_ts(
            pixel_id=pixel.id, predict_at=predict_at, train_horizon=train_horizon,
        )

        # Decompose the `training_ts` to make predictions for the seasonal
        # component and the seasonally adjusted observations separately.
        decomposed_training_ts = methods.decomposition.stl(
            time_series=training_ts,
            frequency=frequency,
            # "Periodic" `ns` parameter => same seasonal component value
            # for observations of the same lag.
            ns=999,
        )

        # Make predictions for the seasonal component by linear extrapolation.
        seasonal_predictions = methods.extrapolate_season.predict(
            training_ts=decomposed_training_ts['seasonal'],
            forecast_interval=actuals_ts.index,
            frequency=frequency,
        )

        # Make predictions with the ARIMA model on the seasonally adjusted time series.
        seasonally_adjusted_predictions = methods.arima.predict(
            training_ts=(
                decomposed_training_ts['trend'] + decomposed_training_ts['residual']
            ),
            forecast_interval=actuals_ts.index,
            # Because the seasonality was taken out before,
            # the `training_ts` has, by definition, a `frequency` of `1`.
            frequency=1,
            seasonal_fit=False,
        )

        # The overall `predictions` are the sum of the separate predictions above.
        # As the linear extrapolation of the seasonal component has no
        # confidence interval, we put the one from the ARIMA model around
        # the extrapolated seasonal component.
        predictions = pd.DataFrame(
            data={
                'actual': actuals_ts,
                'prediction': (
                    seasonal_predictions['prediction']  # noqa:WPS204
                    + seasonally_adjusted_predictions['prediction']
                ),
                'low80': (
                    seasonal_predictions['prediction']
                    + seasonally_adjusted_predictions['low80']
                ),
                'high80': (
                    seasonal_predictions['prediction']
                    + seasonally_adjusted_predictions['high80']
                ),
                'low95': (
                    seasonal_predictions['prediction']
                    + seasonally_adjusted_predictions['low95']
                ),
                'high95': (
                    seasonal_predictions['prediction']
                    + seasonally_adjusted_predictions['high95']
                ),
            },
            index=actuals_ts.index,
        )

        # Sanity checks.
        if len(predictions) != 1:  # pragma: no cover
            raise RuntimeError('real-time models should predict exactly one time step')
        if predictions.isnull().any().any():  # pragma: no cover
            raise RuntimeError('missing predictions in rtarima model')
        if predict_at not in predictions.index:  # pragma: no cover
            raise RuntimeError('missing prediction for `predict_at`')

        return predictions
