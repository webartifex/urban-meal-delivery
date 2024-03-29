"""Test the ORM's `Forecast` model."""

import datetime as dt

import pandas as pd
import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from tests import config as test_config
from urban_meal_delivery import db


MODEL = 'hets'


@pytest.fixture
def forecast(pixel):
    """A `forecast` made in the `pixel` at `NOON`."""
    start_at = dt.datetime(
        test_config.END.year,
        test_config.END.month,
        test_config.END.day,
        test_config.NOON,
    )

    return db.Forecast(
        pixel=pixel,
        start_at=start_at,
        time_step=test_config.LONG_TIME_STEP,
        train_horizon=test_config.LONG_TRAIN_HORIZON,
        model=MODEL,
        actual=12,
        prediction=12.3,
        low80=1.23,
        high80=123.4,
        low95=0.123,
        high95=1234.5,
    )


class TestSpecialMethods:
    """Test special methods in `Forecast`."""

    def test_create_forecast(self, forecast):
        """Test instantiation of a new `Forecast` object."""
        assert forecast is not None

    def test_text_representation(self, forecast):
        """`Forecast` has a non-literal text representation."""
        result = repr(forecast)

        assert (
            result
            == f'<Forecast: {forecast.prediction} for pixel ({forecast.pixel.n_x}|{forecast.pixel.n_y}) at {forecast.start_at}>'  # noqa:E501
        )


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Forecast`."""

    def test_insert_into_database(self, db_session, forecast):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Forecast).count() == 0

        db_session.add(forecast)
        db_session.commit()

        assert db_session.query(db.Forecast).count() == 1

    def test_delete_a_referenced_pixel(self, db_session, forecast):
        """Remove a record that is referenced with a FK."""
        db_session.add(forecast)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Pixel).where(db.Pixel.id == forecast.pixel.id)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_forecasts_to_pixels_via_pixel_id',
        ):
            db_session.execute(stmt)

    @pytest.mark.parametrize('hour', [10, 23])
    def test_invalid_start_at_outside_operating_hours(
        self, db_session, forecast, hour,
    ):
        """Insert an instance with invalid data."""
        forecast.start_at = dt.datetime(
            forecast.start_at.year,
            forecast.start_at.month,
            forecast.start_at.day,
            hour,
        )
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='within_operating_hours',
        ):
            db_session.commit()

    def test_invalid_start_at_not_quarter_of_hour(self, db_session, forecast):
        """Insert an instance with invalid data."""
        forecast.start_at += dt.timedelta(minutes=1)
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='must_be_quarters_of_the_hour',
        ):
            db_session.commit()

    def test_invalid_start_at_seconds_set(self, db_session, forecast):
        """Insert an instance with invalid data."""
        forecast.start_at += dt.timedelta(seconds=1)
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='no_seconds',
        ):
            db_session.commit()

    def test_invalid_start_at_microseconds_set(self, db_session, forecast):
        """Insert an instance with invalid data."""
        forecast.start_at += dt.timedelta(microseconds=1)
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='no_microseconds',
        ):
            db_session.commit()

    @pytest.mark.parametrize('value', [-1, 0])
    def test_positive_time_step(self, db_session, forecast, value):
        """Insert an instance with invalid data."""
        forecast.time_step = value
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='time_step_must_be_positive',
        ):
            db_session.commit()

    @pytest.mark.parametrize('value', [-1, 0])
    def test_positive_train_horizon(self, db_session, forecast, value):
        """Insert an instance with invalid data."""
        forecast.train_horizon = value
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='training_horizon_must_be_positive',
        ):
            db_session.commit()

    def test_non_negative_actuals(self, db_session, forecast):
        """Insert an instance with invalid data."""
        forecast.actual = -1
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='actuals_must_be_non_negative',
        ):
            db_session.commit()

    def test_set_prediction_without_ci(self, db_session, forecast):
        """Sanity check to see that the check constraint ...

        ... "prediction_must_be_within_ci" is not triggered.
        """
        forecast.low80 = None
        forecast.high80 = None
        forecast.low95 = None
        forecast.high95 = None

        db_session.add(forecast)
        db_session.commit()

    def test_ci80_with_missing_low(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.high80 is not None

        forecast.low80 = None
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci_upper_and_lower_bounds',
        ):
            db_session.commit()

    def test_ci95_with_missing_low(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.high95 is not None

        forecast.low95 = None
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci_upper_and_lower_bounds',
        ):
            db_session.commit()

    def test_ci80_with_missing_high(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low80 is not None

        forecast.high80 = None
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci_upper_and_lower_bounds',
        ):
            db_session.commit()

    def test_ci95_with_missing_high(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low95 is not None

        forecast.high95 = None
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci_upper_and_lower_bounds',
        ):
            db_session.commit()

    def test_prediction_smaller_than_low80_with_ci95_set(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low95 is not None
        assert forecast.high95 is not None

        forecast.prediction = forecast.low80 - 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_smaller_than_low80_without_ci95_set(
        self, db_session, forecast,
    ):
        """Insert an instance with invalid data."""
        forecast.low95 = None
        forecast.high95 = None

        forecast.prediction = forecast.low80 - 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_smaller_than_low95_with_ci80_set(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low80 is not None
        assert forecast.high80 is not None

        forecast.prediction = forecast.low95 - 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_smaller_than_low95_without_ci80_set(
        self, db_session, forecast,
    ):
        """Insert an instance with invalid data."""
        forecast.low80 = None
        forecast.high80 = None

        forecast.prediction = forecast.low95 - 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_greater_than_high80_with_ci95_set(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low95 is not None
        assert forecast.high95 is not None

        forecast.prediction = forecast.high80 + 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_greater_than_high80_without_ci95_set(
        self, db_session, forecast,
    ):
        """Insert an instance with invalid data."""
        forecast.low95 = None
        forecast.high95 = None

        forecast.prediction = forecast.high80 + 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_greater_than_high95_with_ci80_set(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low80 is not None
        assert forecast.high80 is not None

        forecast.prediction = forecast.high95 + 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_prediction_greater_than_high95_without_ci80_set(
        self, db_session, forecast,
    ):
        """Insert an instance with invalid data."""
        forecast.low80 = None
        forecast.high80 = None

        forecast.prediction = forecast.high95 + 0.001
        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='prediction_must_be_within_ci',
        ):
            db_session.commit()

    def test_ci80_upper_bound_greater_than_lower_bound(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low80 is not None
        assert forecast.high80 is not None

        # Do not trigger the "ci95_must_be_wider_than_ci80" constraint.
        forecast.low95 = None
        forecast.high95 = None

        forecast.low80, forecast.high80 = (  # noqa:WPS414
            forecast.high80,
            forecast.low80,
        )

        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci_upper_bound_greater_than_lower_bound',
        ):
            db_session.commit()

    def test_ci95_upper_bound_greater_than_lower_bound(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low95 is not None
        assert forecast.high95 is not None

        # Do not trigger the "ci95_must_be_wider_than_ci80" constraint.
        forecast.low80 = None
        forecast.high80 = None

        forecast.low95, forecast.high95 = (  # noqa:WPS414
            forecast.high95,
            forecast.low95,
        )

        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci_upper_bound_greater_than_lower_bound',
        ):
            db_session.commit()

    def test_ci95_is_wider_than_ci80_at_low_end(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.low80 is not None
        assert forecast.low95 is not None

        forecast.low80, forecast.low95 = (forecast.low95, forecast.low80)  # noqa:WPS414

        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci95_must_be_wider_than_ci80',
        ):
            db_session.commit()

    def test_ci95_is_wider_than_ci80_at_high_end(self, db_session, forecast):
        """Insert an instance with invalid data."""
        assert forecast.high80 is not None
        assert forecast.high95 is not None

        forecast.high80, forecast.high95 = (  # noqa:WPS414
            forecast.high95,
            forecast.high80,
        )

        db_session.add(forecast)

        with pytest.raises(
            sa_exc.IntegrityError, match='ci95_must_be_wider_than_ci80',
        ):
            db_session.commit()

    def test_two_predictions_for_same_forecasting_setting(self, db_session, forecast):
        """Insert a record that violates a unique constraint."""
        db_session.add(forecast)
        db_session.commit()

        another_forecast = db.Forecast(
            pixel=forecast.pixel,
            start_at=forecast.start_at,
            time_step=forecast.time_step,
            train_horizon=forecast.train_horizon,
            model=forecast.model,
            actual=forecast.actual,
            prediction=2,
            low80=1,
            high80=3,
            low95=0,
            high95=4,
        )
        db_session.add(another_forecast)

        with pytest.raises(sa_exc.IntegrityError, match='duplicate key value'):
            db_session.commit()


class TestFromDataFrameConstructor:
    """Test the alternative `Forecast.from_dataframe()` constructor."""

    @pytest.fixture
    def prediction_data(self):
        """A `pd.DataFrame` as returned by `*Model.predict()` ...

        ... and used as the `data` argument to `Forecast.from_dataframe()`.

        We assume the `data` come from some vertical forecasting `*Model`
        and contain several rows (= `3` in this example) corresponding
        to different time steps centered around `NOON`.
        """
        noon_start_at = dt.datetime(
            test_config.END.year,
            test_config.END.month,
            test_config.END.day,
            test_config.NOON,
        )

        index = pd.Index(
            [
                noon_start_at - dt.timedelta(minutes=test_config.LONG_TIME_STEP),
                noon_start_at,
                noon_start_at + dt.timedelta(minutes=test_config.LONG_TIME_STEP),
            ],
        )
        index.name = 'start_at'

        return pd.DataFrame(
            data={
                'actual': (11, 12, 13),
                'prediction': (11.3, 12.3, 13.3),
                'low80': (1.123, 1.23, 1.323),
                'high80': (112.34, 123.4, 132.34),
                'low95': (0.1123, 0.123, 0.1323),
                'high95': (1123.45, 1234.5, 1323.45),
            },
            index=index,
        )

    def test_convert_dataframe_into_orm_objects(self, pixel, prediction_data):
        """Call `Forecast.from_dataframe()`."""
        forecasts = db.Forecast.from_dataframe(
            pixel=pixel,
            time_step=test_config.LONG_TIME_STEP,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
            model=MODEL,
            data=prediction_data,
        )

        assert len(forecasts) == 3
        for forecast in forecasts:
            assert isinstance(forecast, db.Forecast)

    @pytest.mark.db
    def test_persist_predictions_into_database(
        self, db_session, pixel, prediction_data,
    ):
        """Call `Forecast.from_dataframe()` and persist the results."""
        forecasts = db.Forecast.from_dataframe(
            pixel=pixel,
            time_step=test_config.LONG_TIME_STEP,
            train_horizon=test_config.LONG_TRAIN_HORIZON,
            model=MODEL,
            data=prediction_data,
        )

        db_session.add_all(forecasts)
        db_session.commit()
