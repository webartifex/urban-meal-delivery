"""CLI script to forecast demand.

The main purpose of this script is to pre-populate the `db.Forecast` table
with demand predictions such that they can readily be used by the
predictive routing algorithms.
"""

import datetime as dt
import sys

import click
from sqlalchemy import func
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import config
from urban_meal_delivery import db
from urban_meal_delivery.console import decorators
from urban_meal_delivery.forecasts import timify


@click.command()
@click.argument('city', default='Paris', type=str)
@click.argument('side_length', default=1000, type=int)
@click.argument('time_step', default=60, type=int)
@click.argument('train_horizon', default=8, type=int)
@decorators.db_revision('8bfb928a31f8')
def tactical_heuristic(  # noqa:C901,WPS213,WPS216,WPS231
    city: str, side_length: int, time_step: int, train_horizon: int,
) -> None:  # pragma: no cover
    """Predict demand for all pixels and days in a city.

    This command makes demand `Forecast`s for all `Pixel`s and days
    for tactical purposes with the heuristic specified in
    `urban_meal_delivery.forecasts.timify.OrderHistory.choose_tactical_model()`.

    According to this heuristic, there is exactly one `Forecast` per
    `Pixel` and time step (e.g., hour of the day with 60-minute time steps)
    given the lengths of the training horizon and a time step. That is so
    as the heuristic chooses the most promising forecasting `*Model`.

    All `Forecast`s are persisted to the database so that they can be readily
    used by the predictive routing algorithms.

    This command first checks, which `Forecast`s still need to be made
    and then does its work. So, it can be interrupted at any point in
    time and then simply continues where it left off the next time it
    is executed.

    Important: In a future revision, this command may need to be adapted such
    that is does not simply obtain the last time step for which a `Forecast`
    was made and continues from there. The reason is that another future command
    may make predictions using all available forecasting `*Model`s per `Pixel`
    and time step.

    Arguments:

    CITY: one of "Bordeaux", "Lyon", or "Paris" (=default)

    SIDE_LENGTH: of a pixel in the grid; defaults to `1000`

    TIME_STEP: length of one time step in minutes; defaults to `60`

    TRAIN_HORIZON: length of the training horizon; defaults to `8`
    """  # noqa:D412,D417,RST215
    # Input validation.

    try:
        city_obj = (
            db.session.query(db.City).filter_by(name=city.title()).one()  # noqa:WPS221
        )
    except orm_exc.NoResultFound:
        click.echo('NAME must be one of "Paris", "Lyon", or "Bordeaux"')
        sys.exit(1)

    for grid in city_obj.grids:
        if grid.side_length == side_length:
            break
    else:
        click.echo(f'SIDE_LENGTH must be in {config.GRID_SIDE_LENGTHS}')
        sys.exit(1)

    if time_step not in config.TIME_STEPS:
        click.echo(f'TIME_STEP must be in {config.TIME_STEPS}')
        sys.exit(1)

    if train_horizon not in config.TRAIN_HORIZONS:
        click.echo(f'TRAIN_HORIZON must be in {config.TRAIN_HORIZONS}')
        sys.exit(1)

    click.echo(
        'Parameters: '
        + f'city="{city}", grid.side_length={side_length}, '
        + f'time_step={time_step}, train_horizon={train_horizon}',
    )

    # Load the historic order data.
    order_history = timify.OrderHistory(grid=grid, time_step=time_step)  # noqa:WPS441
    order_history.aggregate_orders()

    # Run the tactical heuristic.

    for pixel in grid.pixels:  # noqa:WPS441
        # Important: this check may need to be adapted once further
        # commands are added the make `Forecast`s without the heuristic!
        # Continue with forecasting on the day the last prediction was made ...
        last_predict_at = (  # noqa:ECE001
            db.session.query(func.max(db.Forecast.start_at))
            .join(db.Pixel, db.Forecast.pixel_id == db.Pixel.id)
            .join(db.Grid, db.Pixel.grid_id == db.Grid.id)
            .filter(db.Forecast.pixel == pixel)
            .filter(db.Grid.side_length == side_length)
            .filter(db.Forecast.time_step == time_step)
            .filter(db.Forecast.train_horizon == train_horizon)
            .first()
        )[0]
        # ... or start `train_horizon` weeks after the first `Order`
        # if no `Forecast`s are in the database yet.
        if last_predict_at is None:
            predict_day = order_history.first_order_at(pixel_id=pixel.id).date()
            predict_day += dt.timedelta(weeks=train_horizon)
        else:
            predict_day = last_predict_at.date()

        # Go over all days in chronological order ...
        while predict_day <= order_history.last_order_at(pixel_id=pixel.id).date():
            # ... and choose the most promising `*Model` for that day.
            model = order_history.choose_tactical_model(
                pixel_id=pixel.id, predict_day=predict_day, train_horizon=train_horizon,
            )
            click.echo(
                f'Predicting pixel #{pixel.id} in {city} '
                + f'for {predict_day} with {model.name}',
            )

            # Only loop over the time steps corresponding to working hours.
            predict_at = dt.datetime(
                predict_day.year,
                predict_day.month,
                predict_day.day,
                config.SERVICE_START,
            )
            while predict_at.hour < config.SERVICE_END:
                model.make_forecast(
                    pixel=pixel, predict_at=predict_at, train_horizon=train_horizon,
                )

                predict_at += dt.timedelta(minutes=time_step)

            predict_day += dt.timedelta(days=1)
