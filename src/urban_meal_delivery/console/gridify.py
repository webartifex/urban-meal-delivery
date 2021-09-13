"""CLI script to create pixel grids."""

import click

from urban_meal_delivery import config
from urban_meal_delivery import db
from urban_meal_delivery.console import decorators


@click.command()
@decorators.db_revision('e86290e7305e')
def gridify() -> None:  # pragma: no cover  note:b1f68d24
    """Create grids for all cities.

    This command creates grids with pixels of various
    side lengths (specified in `urban_meal_delivery.config`).

    Pixels are only generated if they contain at least one
    (pickup or delivery) address.

    All data are persisted to the database.
    """
    cities = db.session.query(db.City).all()
    click.echo(f'{len(cities)} cities retrieved from the database')

    for city in cities:
        click.echo(f'\nCreating grids for {city.name}')

        for side_length in config.GRID_SIDE_LENGTHS:
            click.echo(f'Creating grid with a side length of {side_length} meters')

            grid = db.Grid.gridify(city=city, side_length=side_length)
            db.session.add(grid)

            click.echo(f' -> created {len(grid.pixels)} pixels')

        # Because the number of assigned addresses is the same across
        # different `side_length`s, we can take any `grid` from the `city`.
        grid = db.session.query(db.Grid).filter_by(city=city).first()
        n_assigned = (
            db.session.query(db.AddressPixelAssociation)
            .filter(db.AddressPixelAssociation.grid_id == grid.id)
            .count()
        )
        click.echo(
            f'=> assigned {n_assigned} out of {len(city.addresses)} addresses in {city.name}',  # noqa:E501
        )

    db.session.commit()
