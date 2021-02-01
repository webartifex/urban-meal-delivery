"""Tests for the `urban_meal_delivery.forecasts.models` sub-package."""


import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import db
from urban_meal_delivery.forecasts import models


MODELS = (
    models.HorizontalETSModel,
    models.RealtimeARIMAModel,
    models.VerticalARIMAModel,
)


@pytest.mark.parametrize('model_cls', MODELS)
class TestGenericForecastingModelProperties:
    """Test everything all concrete `*Model`s have in common.

    The test cases here replace testing the `ForecastingModelABC` class on its own.

    As uncertainty is in the nature of forecasting, we do not test the individual
    point forecasts or confidence intervals themselves. Instead, we confirm
    that all the `*Model`s adhere to the `ForecastingModelABC` generically.
    So, these test cases are more like integration tests conceptually.

    Also, note that some `methods.*.predict()` functions use R behind the scenes.
    """  # noqa:RST215

    def test_create_model(self, model_cls, order_history):
        """Test instantiation of a new and concrete `*Model` object."""
        model = model_cls(order_history=order_history)

        assert model is not None

    def test_model_has_a_name(self, model_cls, order_history):
        """Access the `*Model.name` property."""
        model = model_cls(order_history=order_history)

        result = model.name

        assert isinstance(result, str)

    unique_model_names = set()

    def test_each_model_has_a_unique_name(self, model_cls, order_history):
        """The `*Model.name` values must be unique across all `*Model`s.

        Important: this test case has a side effect that is visible
        across the different parametrized versions of this case!
        """  # noqa:RST215
        model = model_cls(order_history=order_history)

        assert model.name not in self.unique_model_names

        self.unique_model_names.add(model.name)

    @pytest.mark.r
    def test_make_prediction_structure(
        self, model_cls, order_history, pixel, predict_at,
    ):
        """`*Model.predict()` returns a `pd.DataFrame` ...

        ... with known columns.
        """  # noqa:RST215
        model = model_cls(order_history=order_history)

        result = model.predict(
            pixel=pixel,
            predict_at=predict_at,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == [
            'actual',
            'prediction',
            'low80',
            'high80',
            'low95',
            'high95',
        ]

    @pytest.mark.r
    def test_make_prediction_for_given_time_step(
        self, model_cls, order_history, pixel, predict_at,
    ):
        """`*Model.predict()` returns a row for ...

        ... the time step starting at `predict_at`.
        """  # noqa:RST215
        model = model_cls(order_history=order_history)

        result = model.predict(
            pixel=pixel,
            predict_at=predict_at,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert predict_at in result.index

    @pytest.mark.r
    def test_make_prediction_contains_actual_values(
        self, model_cls, order_history, pixel, predict_at,
    ):
        """`*Model.predict()` returns a `pd.DataFrame` ...

        ... where the "actual" and "prediction" columns must not be empty.
        """  # noqa:RST215
        model = model_cls(order_history=order_history)

        result = model.predict(
            pixel=pixel,
            predict_at=predict_at,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert not result['actual'].isnull().any()
        assert not result['prediction'].isnull().any()

    @pytest.mark.db
    @pytest.mark.r
    def test_make_forecast(  # noqa:WPS211
        self, db_session, model_cls, order_history, pixel, predict_at,
    ):
        """`*Model.make_forecast()` returns a `Forecast` object."""  # noqa:RST215
        model = model_cls(order_history=order_history)

        result = model.make_forecast(
            pixel=pixel,
            predict_at=predict_at,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert isinstance(result, db.Forecast)
        assert result.pixel == pixel
        assert result.start_at == predict_at
        assert result.training_horizon == test_config.LONG_TRAIN_HORIZON

    @pytest.mark.db
    @pytest.mark.r
    def test_make_forecast_is_cached(  # noqa:WPS211
        self, db_session, model_cls, order_history, pixel, predict_at,
    ):
        """`*Model.make_forecast()` caches the `Forecast` object."""  # noqa:RST215
        model = model_cls(order_history=order_history)

        assert db_session.query(db.Forecast).count() == 0

        result1 = model.make_forecast(
            pixel=pixel,
            predict_at=predict_at,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        n_cached_forecasts = db_session.query(db.Forecast).count()
        assert n_cached_forecasts >= 1

        result2 = model.make_forecast(
            pixel=pixel,
            predict_at=predict_at,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert n_cached_forecasts == db_session.query(db.Forecast).count()

        assert result1 == result2
