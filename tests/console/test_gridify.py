"""Integration test for the `urban_meal_delivery.console.gridify` module."""

import pytest

import urban_meal_delivery
from urban_meal_delivery import db
from urban_meal_delivery.console import gridify


@pytest.mark.db
def test_two_pixels_with_two_addresses(  # noqa:WPS211
    cli, db_session, monkeypatch, city, make_address, make_restaurant, make_order,
):
    """Two `Address` objects in distinct `Pixel` objects.

    This is roughly the same test case as
    `tests.db.test_grids.test_two_pixels_with_two_addresses`.
    The difference is that the result is written to the database.
    """
    # Create two `Address` objects in distinct `Pixel`s.
    # One `Address` in the lower-left `Pixel`, ...
    address1 = make_address(latitude=48.8357377, longitude=2.2517412)
    # ... and another one in the upper-right one.
    address2 = make_address(latitude=48.8898312, longitude=2.4357622)

    # Locate a `Restaurant` at the two `Address` objects and
    # place one `Order` for each of them so that the `Address`
    # objects are used as `Order.pickup_address`s.
    restaurant1 = make_restaurant(address=address1)
    restaurant2 = make_restaurant(address=address2)
    order1 = make_order(restaurant=restaurant1)
    order2 = make_order(restaurant=restaurant2)

    db_session.add(order1)
    db_session.add(order2)
    db_session.commit()

    side_length = max(city.total_x // 2, city.total_y // 2) + 1

    # Hack the configuration regarding the grids to be created.
    monkeypatch.setattr(urban_meal_delivery.config, 'GRID_SIDE_LENGTHS', [side_length])

    result = cli.invoke(gridify.gridify)

    assert result.exit_code == 0

    assert db_session.query(db.Grid).count() == 1
    assert db_session.query(db.Pixel).count() == 2
