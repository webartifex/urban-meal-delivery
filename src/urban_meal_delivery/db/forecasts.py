"""Provide the ORM's `Forecast` model."""

from __future__ import annotations

from typing import List

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery.db import meta


class Forecast(meta.Base):
    """A demand forecast for a `.pixel` and `.time_step` pair.

    This table is denormalized on purpose to keep things simple. In particular,
    the `.model` and `.actual` hold redundant values.
    """

    __tablename__ = 'forecasts'

    # Columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)  # noqa:WPS125
    pixel_id = sa.Column(sa.Integer, nullable=False, index=True)
    start_at = sa.Column(sa.DateTime, nullable=False)
    time_step = sa.Column(sa.SmallInteger, nullable=False)
    training_horizon = sa.Column(sa.SmallInteger, nullable=False)
    model = sa.Column(sa.Unicode(length=20), nullable=False)
    # We also store the actual order counts for convenient retrieval.
    # A `UniqueConstraint` below ensures that redundant values that
    # are to be expected are consistend across rows.
    actual = sa.Column(sa.SmallInteger, nullable=False)
    # Raw `.prediction`s are stored as `float`s (possibly negative).
    # The rounding is then done on the fly if required.
    prediction = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)
    # The confidence intervals are treated like the `.prediction`s
    # but they may be nullable as some methods do not calculate them.
    low80 = sa.Column(postgresql.DOUBLE_PRECISION, nullable=True)
    high80 = sa.Column(postgresql.DOUBLE_PRECISION, nullable=True)
    low95 = sa.Column(postgresql.DOUBLE_PRECISION, nullable=True)
    high95 = sa.Column(postgresql.DOUBLE_PRECISION, nullable=True)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['pixel_id'], ['pixels.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    EXTRACT(HOUR FROM start_at) < 11
                    OR
                    EXTRACT(HOUR FROM start_at) > 22
                )
            """,
            name='start_at_must_be_within_operating_hours',
        ),
        sa.CheckConstraint(
            'CAST(EXTRACT(MINUTES FROM start_at) AS INTEGER) % 15 = 0',
            name='start_at_minutes_must_be_quarters_of_the_hour',
        ),
        sa.CheckConstraint(
            'EXTRACT(SECONDS FROM start_at) = 0', name='start_at_allows_no_seconds',
        ),
        sa.CheckConstraint(
            'CAST(EXTRACT(MICROSECONDS FROM start_at) AS INTEGER) % 1000000 = 0',
            name='start_at_allows_no_microseconds',
        ),
        sa.CheckConstraint('time_step > 0', name='time_step_must_be_positive'),
        sa.CheckConstraint(
            'training_horizon > 0', name='training_horizon_must_be_positive',
        ),
        sa.CheckConstraint('actual >= 0', name='actuals_must_be_non_negative'),
        sa.CheckConstraint(
            """
                NOT (
                    low80 IS NULL AND high80 IS NOT NULL
                    OR
                    low80 IS NOT NULL AND high80 IS NULL
                    OR
                    low95 IS NULL AND high95 IS NOT NULL
                    OR
                    low95 IS NOT NULL AND high95 IS NULL
               )
            """,
            name='ci_upper_and_lower_bounds',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    prediction < low80
                    OR
                    prediction < low95
                    OR
                    prediction > high80
                    OR
                    prediction > high95
                )
            """,
            name='prediction_must_be_within_ci',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    low80 > high80
                    OR
                    low95 > high95
                )
            """,
            name='ci_upper_bound_greater_than_lower_bound',
        ),
        sa.CheckConstraint(
            """
                NOT (
                    low80 < low95
                    OR
                    high80 > high95
                )
            """,
            name='ci95_must_be_wider_than_ci80',
        ),
        # There can be only one prediction per forecasting setting.
        sa.UniqueConstraint(
            'pixel_id', 'start_at', 'time_step', 'training_horizon', 'model',
        ),
    )

    # Relationships
    pixel = orm.relationship('Pixel', back_populates='forecasts')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}: {prediction} for pixel ({n_x}|{n_y}) at {start_at}>'.format(
            cls=self.__class__.__name__,
            prediction=self.prediction,
            n_x=self.pixel.n_x,
            n_y=self.pixel.n_y,
            start_at=self.start_at,
        )

    @classmethod
    def from_dataframe(  # noqa:WPS211
        cls,
        pixel: db.Pixel,
        time_step: int,
        training_horizon: int,
        model: str,
        data: pd.Dataframe,
    ) -> List[db.Forecast]:
        """Convert results from the forecasting `*Model`s into `Forecast` objects.

        This is an alternative constructor method.

        Background: The functions in `urban_meal_delivery.forecasts.methods`
        return `pd.Dataframe`s with "start_at" (i.e., `pd.Timestamp` objects)
        values in the index and five columns "prediction", "low80", "high80",
        "low95", and "high95" with `np.float` values. The `*Model.predic()`
        methods in `urban_meal_delivery.forecasts.models` then add an "actual"
        column. This constructor converts these results into ORM models.
        Also, the `np.float` values are cast as plain `float` ones as
        otherwise SQLAlchemy and the database would complain.

        Args:
            pixel: in which the forecast is made
            time_step: length of one time step in minutes
            training_horizon: length of the training horizon in weeks
            model: name of the forecasting model
            data: a `pd.Dataframe` as described above (i.e.,
                with the six columns holding `float`s)

        Returns:
            forecasts: the `data` as `Forecast` objects
        """  # noqa:RST215
        forecasts = []

        for timestamp_idx in data.index:
            forecast = cls(
                pixel=pixel,
                start_at=timestamp_idx.to_pydatetime(),
                time_step=time_step,
                training_horizon=training_horizon,
                model=model,
                actual=int(data.loc[timestamp_idx, 'actual']),
                prediction=round(data.loc[timestamp_idx, 'prediction'], 5),
                low80=round(data.loc[timestamp_idx, 'low80'], 5),
                high80=round(data.loc[timestamp_idx, 'high80'], 5),
                low95=round(data.loc[timestamp_idx, 'low95'], 5),
                high95=round(data.loc[timestamp_idx, 'high95'], 5),
            )
            forecasts.append(forecast)

        return forecasts


from urban_meal_delivery import db  # noqa:E402  isort:skip
