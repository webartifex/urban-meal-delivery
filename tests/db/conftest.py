"""Utils for testing the ORM layer."""

import pytest
from alembic import command as migrations_cmd
from alembic import config as migrations_config
from sqlalchemy import orm

from tests.db import fake_data
from urban_meal_delivery import config
from urban_meal_delivery import db


@pytest.fixture(scope='session', params=['all_at_once', 'sequentially'])
def db_connection(request):
    """Create all tables given the ORM models.

    The tables are put into a distinct PostgreSQL schema
    that is removed after all tests are over.

    The database connection used to do that is yielded.

    There are two modes for this fixture:

    - "all_at_once": build up the tables all at once with MetaData.create_all()
    - "sequentially": build up the tables sequentially with `alembic upgrade head`

    This ensures that Alembic's migration files are consistent.
    """
    engine = db.make_engine()
    connection = engine.connect()

    if request.param == 'all_at_once':
        engine.execute(f'CREATE SCHEMA {config.CLEAN_SCHEMA};')
        db.Base.metadata.create_all(connection)
    else:
        cfg = migrations_config.Config('alembic.ini')
        migrations_cmd.upgrade(cfg, 'head')

    try:
        yield connection

    finally:
        connection.execute(f'DROP SCHEMA {config.CLEAN_SCHEMA} CASCADE;')

        if request.param == 'sequentially':
            tmp_alembic_version = f'{config.ALEMBIC_TABLE}_{config.CLEAN_SCHEMA}'
            connection.execute(
                f'DROP TABLE {config.ALEMBIC_TABLE_SCHEMA}.{tmp_alembic_version};',
            )

        connection.close()


@pytest.fixture
def db_session(db_connection):
    """A SQLAlchemy session that rolls back everything after a test case."""
    # Begin the outer most transaction
    # that is rolled back at the end of the test.
    transaction = db_connection.begin()
    # Create a session bound on the same connection as the transaction.
    # Using any other session would not work.
    session_factory = orm.sessionmaker()
    session = session_factory(bind=db_connection)

    try:
        yield session

    finally:
        session.close()
        transaction.rollback()


# Import the fixtures from the `fake_data` sub-package.

make_address = fake_data.make_address
make_courier = fake_data.make_courier
make_customer = fake_data.make_customer
make_order = fake_data.make_order
make_restaurant = fake_data.make_restaurant

address = fake_data.address
city = fake_data.city
city_data = fake_data.city_data
courier = fake_data.courier
customer = fake_data.customer
order = fake_data.order
restaurant = fake_data.restaurant
