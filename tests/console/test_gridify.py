"""Integration test for the `urban_meal_delivery.console.gridify` module."""

import pytest

import urban_meal_delivery
from urban_meal_delivery import db
from urban_meal_delivery.console import gridify


@pytest.mark.db
def test_four_pixels_with_two_addresses(
    cli, db_session, monkeypatch, city, make_address,
):
    """Two `Address` objects in distinct `Pixel` objects.

    This is roughly the same test case as
    `tests.db.test_grids.test_four_pixels_with_two_addresses`.
    The difference is that the result is written to the database.
    """
    # Create two `Address` objects in distinct `Pixel`s.
    city.addresses = [
        # One `Address` in the lower-left `Pixel`, ...
        make_address(latitude=48.8357377, longitude=2.2517412),
        # ... and another one in the upper-right one.
        make_address(latitude=48.8898312, longitude=2.4357622),
    ]

    db_session.add(city)
    db_session.commit()

    side_length = max(city.total_x // 2, city.total_y // 2) + 1

    # Hack the configuration regarding the grids to be created.
    monkeypatch.setattr(urban_meal_delivery.config, 'GRID_SIDE_LENGTHS', [side_length])

    result = cli.invoke(gridify.gridify)

    assert result.exit_code == 0

    assert db_session.query(db.Grid).count() == 1
    assert db_session.query(db.Pixel).count() == 2
