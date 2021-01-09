"""Obtain and work with time series data."""

import datetime as dt

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
