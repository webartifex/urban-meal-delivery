"""Utils for testing the ORM layer."""

import datetime

import pytest
from sqlalchemy import schema

from urban_meal_delivery import config
from urban_meal_delivery import db


@pytest.fixture(scope='session')
def db_engine():
    """Create all tables given the ORM models.

    The tables are put into a distinct PostgreSQL schema
    that is removed after all tests are over.

    The engine used to do that is yielded.
    """
    engine = db.make_engine()
    engine.execute(schema.CreateSchema(config.CLEAN_SCHEMA))
    db.Base.metadata.create_all(engine)

    try:
        yield engine

    finally:
        engine.execute(schema.DropSchema(config.CLEAN_SCHEMA, cascade=True))


@pytest.fixture
def db_session(db_engine):
    """A SQLAlchemy session that rolls back everything after a test case."""
    connection = db_engine.connect()
    # Begin the outer most transaction
    # that is rolled back at the end of the test.
    transaction = connection.begin()
    # Create a session bound on the same connection as the transaction.
    # Using any other session would not work.
    Session = db.make_session_factory()  # noqa:N806
    session = Session(bind=connection)

    try:
        yield session

    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def address_data():
    """The data for an Address object in Paris."""
    return {
        'id': 1,
        '_primary_id': 1,  # => "itself"
        'created_at': datetime.datetime(2020, 1, 2, 3, 4, 5),
        'place_id': 'ChIJxSr71vZt5kcRoFHY4caCCxw',
        'latitude': 48.85313,
        'longitude': 2.37461,
        '_city_id': 1,
        'city_name': 'St. German',
        'zip_code': '75011',
        'street': '42 Rue De Charonne',
        'floor': None,
    }


@pytest.fixture
def address(address_data, city):
    """An Address object."""
    address = db.Address(**address_data)
    address.city = city
    return address


@pytest.fixture
def address2_data():
    """The data for an Address object in Paris."""
    return {
        'id': 2,
        '_primary_id': 2,  # => "itself"
        'created_at': datetime.datetime(2020, 1, 2, 4, 5, 6),
        'place_id': 'ChIJs-9a6QZy5kcRY8Wwk9Ywzl8',
        'latitude': 48.852196,
        'longitude': 2.373937,
        '_city_id': 1,
        'city_name': 'Paris',
        'zip_code': '75011',
        'street': 'Rue De Charonne 3',
        'floor': 2,
    }


@pytest.fixture
def address2(address2_data, city):
    """An Address object."""
    address2 = db.Address(**address2_data)
    address2.city = city
    return address2


@pytest.fixture
def city_data():
    """The data for the City object modeling Paris."""
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
    """A City object."""
    return db.City(**city_data)


@pytest.fixture
def courier_data():
    """The data for a Courier object."""
    return {
        'id': 1,
        'created_at': datetime.datetime(2020, 1, 2, 3, 4, 5),
        'vehicle': 'bicycle',
        'historic_speed': 7.89,
        'capacity': 100,
        'pay_per_hour': 750,
        'pay_per_order': 200,
    }


@pytest.fixture
def courier(courier_data):
    """A Courier object."""
    return db.Courier(**courier_data)


@pytest.fixture
def customer_data():
    """The data for the Customer object."""
    return {'id': 1}


@pytest.fixture
def customer(customer_data):
    """A Customer object."""
    return db.Customer(**customer_data)


@pytest.fixture
def order_data():
    """The data for an ad-hoc Order object."""
    return {
        'id': 1,
        '_delivery_id': 1,
        '_customer_id': 1,
        'placed_at': datetime.datetime(2020, 1, 2, 11, 55, 11),
        'ad_hoc': True,
        'scheduled_delivery_at': None,
        'scheduled_delivery_at_corrected': None,
        'first_estimated_delivery_at': datetime.datetime(2020, 1, 2, 12, 35, 0),
        'cancelled': False,
        'cancelled_at': None,
        'cancelled_at_corrected': None,
        'sub_total': 2000,
        'delivery_fee': 250,
        'total': 2250,
        '_restaurant_id': 1,
        'restaurant_notified_at': datetime.datetime(2020, 1, 2, 12, 5, 5),
        'restaurant_notified_at_corrected': False,
        'restaurant_confirmed_at': datetime.datetime(2020, 1, 2, 12, 5, 25),
        'restaurant_confirmed_at_corrected': False,
        'estimated_prep_duration': 900,
        'estimated_prep_duration_corrected': False,
        'estimated_prep_buffer': 480,
        '_courier_id': 1,
        'dispatch_at': datetime.datetime(2020, 1, 2, 12, 5, 1),
        'dispatch_at_corrected': False,
        'courier_notified_at': datetime.datetime(2020, 1, 2, 12, 6, 2),
        'courier_notified_at_corrected': False,
        'courier_accepted_at': datetime.datetime(2020, 1, 2, 12, 6, 17),
        'courier_accepted_at_corrected': False,
        'utilization': 50,
        '_pickup_address_id': 1,
        'reached_pickup_at': datetime.datetime(2020, 1, 2, 12, 16, 21),
        'pickup_at': datetime.datetime(2020, 1, 2, 12, 18, 1),
        'pickup_at_corrected': False,
        'pickup_not_confirmed': False,
        'left_pickup_at': datetime.datetime(2020, 1, 2, 12, 19, 45),
        'left_pickup_at_corrected': False,
        '_delivery_address_id': 2,
        'reached_delivery_at': datetime.datetime(2020, 1, 2, 12, 27, 33),
        'delivery_at': datetime.datetime(2020, 1, 2, 12, 29, 55),
        'delivery_at_corrected': False,
        'delivery_not_confirmed': False,
        '_courier_waited_at_delivery': False,
        'logged_delivery_distance': 500,
        'logged_avg_speed': 7.89,
        'logged_avg_speed_distance': 490,
    }


@pytest.fixture
def order(  # noqa:WPS211 pylint:disable=too-many-arguments
    order_data, customer, restaurant, courier, address, address2,
):
    """An Order object."""
    order = db.Order(**order_data)
    order.customer = customer
    order.restaurant = restaurant
    order.courier = courier
    order.pickup_address = address
    order.delivery_address = address2
    return order


@pytest.fixture
def restaurant_data():
    """The data for the Restaurant object."""
    return {
        'id': 1,
        'created_at': datetime.datetime(2020, 1, 2, 3, 4, 5),
        'name': 'Vevay',
        '_address_id': 1,
        'estimated_prep_duration': 1000,
    }


@pytest.fixture
def restaurant(restaurant_data, address):
    """A Restaurant object."""
    restaurant = db.Restaurant(**restaurant_data)
    restaurant.address = address
    return restaurant
