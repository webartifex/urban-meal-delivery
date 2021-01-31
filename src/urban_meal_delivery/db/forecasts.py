"""Provide the ORM's `Forecast` model."""

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import postgresql

from urban_meal_delivery.db import meta


class Forecast(meta.Base):
    """A demand forecast for a `.pixel` and `.time_step` pair.

    This table is denormalized on purpose to keep things simple.
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
