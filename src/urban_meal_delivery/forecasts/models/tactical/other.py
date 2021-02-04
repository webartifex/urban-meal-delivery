"""Forecasting `*Model`s to predict demand for tactical purposes ...

... that cannot be classified into either "horizontal", "vertical",
or "real-time".
"""  # noqa:RST215

import datetime as dt

import pandas as pd

from urban_meal_delivery import db
from urban_meal_delivery.forecasts.models import base


class TrivialModel(base.ForecastingModelABC):
    """A trivial model predicting `0` demand.

    No need to distinguish between a "horizontal", "vertical", or
    "real-time" model here as all give the same prediction for all time steps.
    """

    name = 'trivial'

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
        # Generate the historic order time series mainly to check if a valid
        # `training_ts` exists (i.e., the demand history is long enough).
        _, frequency, actuals_ts = self._order_history.make_horizontal_ts(
            pixel_id=pixel.id, predict_at=predict_at, train_horizon=train_horizon,
        )

        # Sanity checks.
        if frequency != 7:  # pragma: no cover
            raise RuntimeError('`frequency` should be `7`')
        if len(actuals_ts) != 1:  # pragma: no cover
            raise RuntimeError(
                'the trivial model can only predict one step into the future',
            )

        # The "prediction" is simply `0.0`.
        predictions = pd.DataFrame(
            data={
                'actual': actuals_ts,
                'prediction': 0.0,
                'low80': float('NaN'),
                'high80': float('NaN'),
                'low95': float('NaN'),
                'high95': float('NaN'),
            },
            index=actuals_ts.index,
        )

        # Sanity checks.
        if predictions['actual'].isnull().any():  # pragma: no cover
            raise RuntimeError('missing actuals in trivial model')
        if predict_at not in predictions.index:  # pragma: no cover
            raise RuntimeError('missing prediction for `predict_at`')

        return predictions
