"""Fake data for testing the ORM layer."""

import pytest

from urban_meal_delivery import db


@pytest.fixture
def city_data():
    """The data for the one and only `City` object as a `dict`."""
    return {
        'id': 1,
        'name': 'Paris',
        'kml': "<?xml version='1.0' encoding='UTF-8'?> ...",
        '_center_latitude': 48.856614,
        '_center_longitude': 2.3522219,
        '_northeast_latitude': 48.9021449,
        '_northeast_longitude': 2.4699208,
        '_southwest_latitude': 48.815573,
        '_southwest_longitude': 2.225193,
        'initial_zoom': 12,
    }


@pytest.fixture
def city(city_data):
    """The one and only `City` object."""
    return db.City(**city_data)


@pytest.fixture
def address(make_address):
    """An `Address` object in the `city`."""
    return make_address()


@pytest.fixture
def courier(make_courier):
    """A `Courier` object."""
    return make_courier()


@pytest.fixture
def customer(make_customer):
    """A `Customer` object."""
    return make_customer()


@pytest.fixture
def restaurant(address, make_restaurant):
    """A `Restaurant` object located at the `address`."""
    return make_restaurant(address=address)


@pytest.fixture
def order(make_order, restaurant):
    """An `Order` object for the `restaurant`."""
    return make_order(restaurant=restaurant)


@pytest.fixture
def grid(city):
    """A `Grid` with a pixel area of 1 square kilometer."""
    return db.Grid(city=city, side_length=1000)


@pytest.fixture
def pixel(grid):
    """The `Pixel` in the lower-left corner of the `grid`."""
    return db.Pixel(grid=grid, n_x=0, n_y=0)
