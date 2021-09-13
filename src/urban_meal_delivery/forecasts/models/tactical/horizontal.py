"""Horizontal forecasting `*Model`s to predict demand for tactical purposes.

Horizontal `*Model`s take the historic order counts only from time steps
corresponding to the same time of day as the one to be predicted (i.e., the
one starting at `predict_at`). Then, they make a prediction for only one day
into the future. Thus, the training time series have a `frequency` of `7`, the
number of days in a week.
"""  # noqa:RST215

import datetime as dt

import pandas as pd

from urban_meal_delivery import db
from urban_meal_delivery.forecasts import methods
from urban_meal_delivery.forecasts.models import base


class HorizontalETSModel(base.ForecastingModelABC):
    """The ETS model applied on a horizontal time series."""

    name = 'hets'

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
        # Generate the historic (and horizontal) order time series.
        training_ts, frequency, actuals_ts = self._order_history.make_horizontal_ts(
            pixel_id=pixel.id, predict_at=predict_at, train_horizon=train_horizon,
        )

        # Sanity check.
        if frequency != 7:  # pragma: no cover
            raise RuntimeError('`frequency` should be `7`')

        # Make `predictions` with the seasonal ETS method ("ZZZ" model).
        predictions = methods.ets.predict(
            training_ts=training_ts,
            forecast_interval=pd.DatetimeIndex(actuals_ts.index),
            frequency=frequency,  # `== 7`, the number of weekdays
            seasonal_fit=True,  # because there was no decomposition before
        )

        predictions.insert(loc=0, column='actual', value=actuals_ts)

        # Sanity checks.
        if predictions.isnull().sum().any():  # pragma: no cover
            raise RuntimeError('missing predictions in hets model')
        if predict_at not in predictions.index:  # pragma: no cover
            raise RuntimeError('missing prediction for `predict_at`')

        return predictions


class HorizontalSMAModel(base.ForecastingModelABC):
    """A simple moving average model applied on a horizontal time series."""

    name = 'hsma'

    def predict(
        self, pixel: db.Pixel, predict_at: dt.datetime, train_horizon: int,
    ) -> pd.DataFrame:
        """Predict demand for a time step.

        Args:
            pixel: pixel in which the prediction is made
            predict_at: time step (i.e., "start_at") to make the prediction for
            train_horizon: weeks of historic data used to predict `predict_at`

        Returns:
            actual order counts (i.e., the "actual" column) and
                point forecasts (i.e., the "prediction" column);
                this model does not support confidence intervals;
                contains one row for the `predict_at` time step

        # noqa:DAR401 RuntimeError
        """
        # Generate the historic (and horizontal) order time series.
        training_ts, frequency, actuals_ts = self._order_history.make_horizontal_ts(
            pixel_id=pixel.id, predict_at=predict_at, train_horizon=train_horizon,
        )

        # Sanity checks.
        if frequency != 7:  # pragma: no cover
            raise RuntimeError('`frequency` should be `7`')
        if len(actuals_ts) != 1:  # pragma: no cover
            raise RuntimeError(
                'the hsma model can only predict one step into the future',
            )

        # The "prediction" is calculated as the `np.mean()`.
        # As the `training_ts` covers only full week horizons,
        # no adjustment regarding the weekly seasonality is needed.
        predictions = pd.DataFrame(
            data={
                'actual': actuals_ts,
                'prediction': training_ts.values.mean(),
                'low80': float('NaN'),
                'high80': float('NaN'),
                'low95': float('NaN'),
                'high95': float('NaN'),
            },
            index=actuals_ts.index,
        )

        # Sanity checks.
        if (  # noqa:WPS337
            predictions[['actual', 'prediction']].isnull().any().any()
        ):  # pragma: no cover

            raise RuntimeError('missing predictions in hsma model')
        if predict_at not in predictions.index:  # pragma: no cover
            raise RuntimeError('missing prediction for `predict_at`')

        return predictions
