"""The abstract blueprint for a forecasting `*Model`."""

import abc
import datetime as dt

import pandas as pd

from urban_meal_delivery import db
from urban_meal_delivery.forecasts import timify


class ForecastingModelABC(abc.ABC):
    """An abstract interface of a forecasting `*Model`."""

    def __init__(self, order_history: timify.OrderHistory) -> None:
        """Initialize a new forecasting model.

        Args:
            order_history: an abstraction providing the time series data
        """
        self._order_history = order_history

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The name of the model.

        Used to identify `Forecast`s of the same `*Model` in the database.
        So, these must be chosen carefully and must not be changed later on!

        Example: "hets" or "varima" for tactical demand forecasting
        """

    @abc.abstractmethod
    def predict(
        self, pixel: db.Pixel, predict_at: dt.datetime, train_horizon: int,
    ) -> pd.DataFrame:
        """Concrete implementation of how a `*Model` makes a prediction.

        This method is called by the unified `*Model.make_forecast()` method,
        which implements the caching logic with the database.

        Args:
            pixel: pixel in which the prediction is made
            predict_at: time step (i.e., "start_at") to make the prediction for
            train_horizon: weeks of historic data used to predict `predict_at`

        Returns:
            actuals, predictions, and possibly 80%/95% confidence intervals;
                includes a row for the time step starting at `predict_at` and
                may contain further rows for other time steps on the same day
        """  # noqa:DAR202

    def make_forecast(
        self, pixel: db.Pixel, predict_at: dt.datetime, train_horizon: int,
    ) -> db.Forecast:
        """Make a forecast for the time step starting at `predict_at`.

        Important: This method uses a unified `predict_at` argument.
        Some `*Model`s, in particular vertical ones, are only trained once per
        day and then make a prediction for all time steps on that day, and
        therefore, work with a `predict_day` argument instead of `predict_at`
        behind the scenes. Then, all `Forecast`s are stored into the database
        and only the one starting at `predict_at` is returned.

        Args:
            pixel: pixel in which the `Forecast` is made
            predict_at: time step (i.e., "start_at") to make the `Forecast` for
            train_horizon: weeks of historic data used to forecast `predict_at`

        Returns:
            actual, prediction, and possibly 80%/95% confidence intervals
                for the time step starting at `predict_at`

        # noqa:DAR401 RuntimeError
        """
        if (  # noqa:WPS337
            cached_forecast := db.session.query(db.Forecast)  # noqa:ECE001,WPS221
            .filter_by(pixel=pixel)
            .filter_by(start_at=predict_at)
            .filter_by(time_step=self._order_history.time_step)
            .filter_by(train_horizon=train_horizon)
            .filter_by(model=self.name)
            .first()
        ) :
            return cached_forecast

        # Horizontal and real-time `*Model`s return a `pd.DataFrame` with one
        # row corresponding to the time step starting at `predict_at` whereas
        # vertical models return several rows, covering all time steps of a day.
        predictions = self.predict(pixel, predict_at, train_horizon)

        # Convert the `predictions` into a `list` of `Forecast` objects.
        forecasts = db.Forecast.from_dataframe(
            pixel=pixel,
            time_step=self._order_history.time_step,
            train_horizon=train_horizon,
            model=self.name,
            data=predictions,
        )

        # We persist all `Forecast`s into the database to
        # not have to run the same model training again.
        db.session.add_all(forecasts)
        db.session.commit()

        # The one `Forecast` object asked for must be in `forecasts`
        # if the concrete `*Model.predict()` method works correctly; ...
        for forecast in forecasts:
            if forecast.start_at == predict_at:
                return forecast

        # ..., however, we put in a loud error, just in case.
        raise RuntimeError(  # pragma: no cover
            '`Forecast` for `predict_at` was not returned by `*Model.predict()`',
        )
