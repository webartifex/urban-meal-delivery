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
    method = sa.Column(sa.Unicode(length=20), nullable=False)  # noqa:WPS432
    # Raw `.prediction`s are stored as `float`s (possibly negative).
    # The rounding is then done on the fly if required.
    prediction = sa.Column(postgresql.DOUBLE_PRECISION, nullable=False)

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
        # There can be only one prediction per forecasting setting.
        sa.UniqueConstraint(
            'pixel_id', 'start_at', 'time_step', 'training_horizon', 'method',
        ),
    )

    # Relationships
    pixel = orm.relationship('Pixel', back_populates='forecasts')
