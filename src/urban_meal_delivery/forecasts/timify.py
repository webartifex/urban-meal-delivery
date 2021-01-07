"""Obtain and work with time series data."""

import datetime

import pandas as pd

from urban_meal_delivery import config
from urban_meal_delivery import db


def aggregate_orders(grid: db.Grid, time_step: int) -> pd.DataFrame:  # pragma: no cover
    """Obtain a time series of the ad-hoc `Order` totals.

    Args:
        grid: pixel grid used to aggregate orders spatially
        time_step: interval length (in minutes) into which orders are aggregated

    Returns:
        order_totals: `DataFrame` with a `MultiIndex` of the "pixel_id"s and
            beginnings of the intervals (i.e., "start_at"s); the sole column
            with data is "total_orders"
    """
    # `data` is probably missing "pixel_id"-"start_at" pairs.
    # This happens whenever there is no demand in the `Pixel` in the given `time_step`.
    data = pd.read_sql_query(
        f"""-- # noqa:WPS221
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
                        EXTRACT(MINUTES FROM orders.placed_at)::INTEGER % {time_step}
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
                            city_id = {grid.city.id}
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
                        grid_id = {grid.id}
                        AND
                        city_id = {grid.city.id} -- city_id is redundant -> sanity check
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
    start = datetime.datetime(
        start_day.year, start_day.month, start_day.day, config.SERVICE_START,
    )
    end_day = data.index.levels[1].max().date()
    end = datetime.datetime(
        end_day.year, end_day.month, end_day.day, config.SERVICE_END,
    )

    # ... and all possible `tuple`s of "pixel_id"-"start_at" combinations.
    # The "start_at" values must lie within the operating hours.
    gen = (
        (pixel_id, start_at)
        for pixel_id in sorted(data.index.levels[0])
        for start_at in pd.date_range(start, end, freq=f'{time_step}T')
        if config.SERVICE_START <= start_at.time().hour < config.SERVICE_END
    )

    # Re-index `data` filling in `0`s where there is no demand.
    index = pd.MultiIndex.from_tuples(gen)
    index.names = ['pixel_id', 'start_at']

    return data.reindex(index, fill_value=0)
