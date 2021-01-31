"""Obtain and work with time series data."""

import datetime as dt
from typing import Tuple

import pandas as pd

from urban_meal_delivery import config
from urban_meal_delivery import db


class OrderHistory:
    """Generate time series from the `Order` model in the database.

    The purpose of this class is to abstract away the managing of the order data
    in memory and the slicing the data into various kinds of time series.
    """

    def __init__(self, grid: db.Grid, time_step: int) -> None:
        """Initialize a new `OrderHistory` object.

        Args:
            grid: pixel grid used to aggregate orders spatially
            time_step: interval length (in minutes) into which orders are aggregated

        # noqa:DAR401 RuntimeError
        """
        self._grid = grid
        self._time_step = time_step

        # Number of daily time steps must be a whole multiple of `time_step` length.
        n_daily_time_steps = (
            60 * (config.SERVICE_END - config.SERVICE_START) / time_step
        )
        if n_daily_time_steps != int(n_daily_time_steps):  # pragma: no cover
            raise RuntimeError('Internal error: configuration has invalid TIME_STEPS')
        self._n_daily_time_steps = int(n_daily_time_steps)

        # The `_data` are populated by `.aggregate_orders()`.
        self._data = None

    @property
    def time_step(self) -> int:
        """The length of one time step."""
        return self._time_step

    @property
    def totals(self) -> pd.DataFrame:
        """The order totals by `Pixel` and `.time_step`.

        The returned object should not be mutated!

        Returns:
            order_totals: a one-column `DataFrame` with a `MultiIndex` of the
                "pixel_id"s and "start_at"s (i.e., beginnings of the intervals);
                the column with data is "total_orders"
        """
        if self._data is None:
            self._data = self.aggregate_orders()

        return self._data

    def aggregate_orders(self) -> pd.DataFrame:  # pragma: no cover
        """Generate and load all order totals from the database."""
        # `data` is probably missing "pixel_id"-"start_at" pairs.
        # This happens when there is no demand in the `Pixel` in the given `time_step`.
        data = pd.read_sql_query(
            f"""-- # noqa:E501,WPS221
            SELECT
                pixel_id,
                start_at,
                COUNT(*) AS total_orders
            FROM (
                SELECT
                    pixel_id,
                    placed_at_without_seconds - minutes_to_be_cut AS start_at
                FROM (
                    SELECT
                        pixels.pixel_id,
                        DATE_TRUNC('MINUTE', orders.placed_at) AS placed_at_without_seconds,
                        ((
                            EXTRACT(MINUTES FROM orders.placed_at)::INTEGER % {self._time_step}
                        )::TEXT || ' MINUTES')::INTERVAL
                            AS minutes_to_be_cut
                    FROM (
                        SELECT
                            id,
                            placed_at,
                            pickup_address_id
                        FROM
                            {config.CLEAN_SCHEMA}.orders
                        INNER JOIN (
                            SELECT
                                id AS address_id
                            FROM
                                {config.CLEAN_SCHEMA}.addresses
                            WHERE
                                city_id = {self._grid.city.id}
                        ) AS in_city
                            ON orders.pickup_address_id = in_city.address_id
                        WHERE
                            ad_hoc IS TRUE
                    ) AS
                        orders
                    INNER JOIN (
                        SELECT
                            address_id,
                            pixel_id
                        FROM
                            {config.CLEAN_SCHEMA}.addresses_pixels
                        WHERE
                            grid_id = {self._grid.id}
                            AND
                            city_id = {self._grid.city.id} -- redundant -> sanity check
                    ) AS pixels
                        ON orders.pickup_address_id = pixels.address_id
                ) AS placed_at_aggregated_into_start_at
            ) AS pixel_start_at_combinations
            GROUP BY
                pixel_id,
                start_at
            ORDER BY
                pixel_id,
                start_at;
            """,
            con=db.connection,
            index_col=['pixel_id', 'start_at'],
        )

        if data.empty:
            return data

        # Calculate the first and last "start_at" value ...
        start_day = data.index.levels[1].min().date()
        start = dt.datetime(
            start_day.year, start_day.month, start_day.day, config.SERVICE_START,
        )
        end_day = data.index.levels[1].max().date()
        end = dt.datetime(end_day.year, end_day.month, end_day.day, config.SERVICE_END)
        # ... and all possible `tuple`s of "pixel_id"-"start_at" combinations.
        # The "start_at" values must lie within the operating hours.
        gen = (
            (pixel_id, start_at)
            for pixel_id in sorted(data.index.levels[0])
            for start_at in pd.date_range(start, end, freq=f'{self._time_step}T')
            if config.SERVICE_START <= start_at.hour < config.SERVICE_END
        )

        # Re-index `data` filling in `0`s where there is no demand.
        index = pd.MultiIndex.from_tuples(gen)
        index.names = ['pixel_id', 'start_at']

        return data.reindex(index, fill_value=0)

    def make_horizontal_time_series(  # noqa:WPS210
        self, pixel_id: int, predict_at: dt.datetime, train_horizon: int,
    ) -> Tuple[pd.Series, int, pd.Series]:
        """Slice a horizontal time series out of the `.totals`.

        Create a time series covering `train_horizon` weeks that can be used
        for training a forecasting model to predict the demand at `predict_at`.

        For explanation of the terms "horizontal", "vertical", and "real-time"
        in the context of time series, see section 3.2 in the following paper:
        https://github.com/webartifex/urban-meal-delivery-demand-forecasting/blob/main/paper.pdf

        Args:
            pixel_id: pixel in which the time series is aggregated
            predict_at: time step (i.e., "start_at") for which a prediction is made
            train_horizon: weeks of historic data used to predict `predict_at`

        Returns:
            training time series, frequency, actual order count at `predict_at`

        Raises:
            LookupError: `pixel_id` not in `grid` or `predict_at` not in `.totals`
            RuntimeError: desired time series slice is not entirely in `.totals`
        """
        try:
            intra_pixel = self.totals.loc[pixel_id]
        except KeyError:
            raise LookupError('The `pixel_id` is not in the `grid`') from None

        if predict_at >= config.CUTOFF_DAY:  # pragma: no cover
            raise RuntimeError('Internal error: cannot predict beyond the given data')

        # The first and last training day are just before the `predict_at` day
        # and span exactly `train_horizon` weeks covering only the times of the
        # day equal to the hour/minute of `predict_at`.
        first_train_day = predict_at.date() - dt.timedelta(weeks=train_horizon)
        first_start_at = dt.datetime(
            first_train_day.year,
            first_train_day.month,
            first_train_day.day,
            predict_at.hour,
            predict_at.minute,
        )
        last_train_day = predict_at.date() - dt.timedelta(days=1)
        last_start_at = dt.datetime(
            last_train_day.year,
            last_train_day.month,
            last_train_day.day,
            predict_at.hour,
            predict_at.minute,
        )

        # The frequency is the number of weekdays.
        frequency = 7

        # Take only the counts at the `predict_at` time.
        training_ts = intra_pixel.loc[
            first_start_at : last_start_at : self._n_daily_time_steps,  # type: ignore
            'total_orders',
        ]
        if len(training_ts) != frequency * train_horizon:
            raise RuntimeError('Not enough historic data for `predict_at`')

        actuals_ts = intra_pixel.loc[[predict_at], 'total_orders']
        if not len(actuals_ts):  # pragma: no cover
            raise LookupError('`predict_at` is not in the order history')

        return training_ts, frequency, actuals_ts

    def make_vertical_time_series(  # noqa:WPS210
        self, pixel_id: int, predict_day: dt.date, train_horizon: int,
    ) -> Tuple[pd.Series, int, pd.Series]:
        """Slice a vertical time series out of the `.totals`.

        Create a time series covering `train_horizon` weeks that can be used
        for training a forecasting model to predict the demand on the `predict_day`.

        For explanation of the terms "horizontal", "vertical", and "real-time"
        in the context of time series, see section 3.2 in the following paper:
        https://github.com/webartifex/urban-meal-delivery-demand-forecasting/blob/main/paper.pdf

        Args:
            pixel_id: pixel in which the time series is aggregated
            predict_day: day for which predictions are made
            train_horizon: weeks of historic data used to predict `predict_at`

        Returns:
            training time series, frequency, actual order counts on `predict_day`

        Raises:
            LookupError: `pixel_id` not in `grid` or `predict_day` not in `.totals`
            RuntimeError: desired time series slice is not entirely in `.totals`
        """
        try:
            intra_pixel = self.totals.loc[pixel_id]
        except KeyError:
            raise LookupError('The `pixel_id` is not in the `grid`') from None

        if predict_day >= config.CUTOFF_DAY.date():  # pragma: no cover
            raise RuntimeError('Internal error: cannot predict beyond the given data')

        # The first and last training day are just before the `predict_day`
        # and span exactly `train_horizon` weeks covering all times of the day.
        first_train_day = predict_day - dt.timedelta(weeks=train_horizon)
        first_start_at = dt.datetime(
            first_train_day.year,
            first_train_day.month,
            first_train_day.day,
            config.SERVICE_START,
            0,
        )
        last_train_day = predict_day - dt.timedelta(days=1)
        last_start_at = dt.datetime(
            last_train_day.year,
            last_train_day.month,
            last_train_day.day,
            config.SERVICE_END,  # subtract one `time_step` below
            0,
        ) - dt.timedelta(minutes=self._time_step)

        # The frequency is the number of weekdays times the number of daily time steps.
        frequency = 7 * self._n_daily_time_steps

        # Take all the counts between `first_train_day` and `last_train_day`.
        training_ts = intra_pixel.loc[
            first_start_at:last_start_at,  # type: ignore
            'total_orders',
        ]
        if len(training_ts) != frequency * train_horizon:
            raise RuntimeError('Not enough historic data for `predict_day`')

        first_prediction_at = dt.datetime(
            predict_day.year,
            predict_day.month,
            predict_day.day,
            config.SERVICE_START,
            0,
        )
        last_prediction_at = dt.datetime(
            predict_day.year,
            predict_day.month,
            predict_day.day,
            config.SERVICE_END,  # subtract one `time_step` below
            0,
        ) - dt.timedelta(minutes=self._time_step)

        actuals_ts = intra_pixel.loc[
            first_prediction_at:last_prediction_at,  # type: ignore
            'total_orders',
        ]
        if not len(actuals_ts):  # pragma: no cover
            raise LookupError('`predict_day` is not in the order history')

        return training_ts, frequency, actuals_ts

    def make_real_time_time_series(  # noqa:WPS210
        self, pixel_id: int, predict_at: dt.datetime, train_horizon: int,
    ) -> Tuple[pd.Series, int, pd.Series]:
        """Slice a vertical real-time time series out of the `.totals`.

        Create a time series covering `train_horizon` weeks that can be used
        for training a forecasting model to predict the demand at `predict_at`.

        For explanation of the terms "horizontal", "vertical", and "real-time"
        in the context of time series, see section 3.2 in the following paper:
        https://github.com/webartifex/urban-meal-delivery-demand-forecasting/blob/main/paper.pdf

        Args:
            pixel_id: pixel in which the time series is aggregated
            predict_at: time step (i.e., "start_at") for which a prediction is made
            train_horizon: weeks of historic data used to predict `predict_at`

        Returns:
            training time series, frequency, actual order count at `predict_at`

        Raises:
            LookupError: `pixel_id` not in `grid` or `predict_at` not in `.totals`
            RuntimeError: desired time series slice is not entirely in `.totals`
        """
        try:
            intra_pixel = self.totals.loc[pixel_id]
        except KeyError:
            raise LookupError('The `pixel_id` is not in the `grid`') from None

        if predict_at >= config.CUTOFF_DAY:  # pragma: no cover
            raise RuntimeError('Internal error: cannot predict beyond the given data')

        # The first and last training day are just before the `predict_at` day
        # and span exactly `train_horizon` weeks covering all times of the day,
        # including times on the `predict_at` day that are earlier than `predict_at`.
        first_train_day = predict_at.date() - dt.timedelta(weeks=train_horizon)
        first_start_at = dt.datetime(
            first_train_day.year,
            first_train_day.month,
            first_train_day.day,
            config.SERVICE_START,
            0,
        )
        # Predicting the first time step on the `predict_at` day is a corner case.
        # Then, the previous day is indeed the `last_train_day`. Predicting any
        # other time step implies that the `predict_at` day is the `last_train_day`.
        # `last_train_time` is the last "start_at" before the one being predicted.
        if predict_at.hour == config.SERVICE_START:
            last_train_day = predict_at.date() - dt.timedelta(days=1)
            last_train_time = dt.time(config.SERVICE_END, 0)
        else:
            last_train_day = predict_at.date()
            last_train_time = predict_at.time()
        last_start_at = dt.datetime(
            last_train_day.year,
            last_train_day.month,
            last_train_day.day,
            last_train_time.hour,
            last_train_time.minute,
        ) - dt.timedelta(minutes=self._time_step)

        # The frequency is the number of weekdays times the number of daily time steps.
        frequency = 7 * self._n_daily_time_steps

        # Take all the counts between `first_train_day` and `last_train_day`,
        # including the ones on the `predict_at` day prior to `predict_at`.
        training_ts = intra_pixel.loc[
            first_start_at:last_start_at,  # type: ignore
            'total_orders',
        ]
        n_time_steps_on_predict_day = (
            (
                predict_at
                - dt.datetime(
                    predict_at.year,
                    predict_at.month,
                    predict_at.day,
                    config.SERVICE_START,
                    0,
                )
            ).seconds
            // 60  # -> minutes
            // self._time_step
        )
        if len(training_ts) != frequency * train_horizon + n_time_steps_on_predict_day:
            raise RuntimeError('Not enough historic data for `predict_day`')

        actuals_ts = intra_pixel.loc[[predict_at], 'total_orders']
        if not len(actuals_ts):  # pragma: no cover
            raise LookupError('`predict_at` is not in the order history')

        return training_ts, frequency, actuals_ts
