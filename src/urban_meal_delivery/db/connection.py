"""Provide connection utils for the ORM layer.

This module defines fully configured `engine`, `connection`, and `session`
objects to be used as globals within the `urban_meal_delivery` package.

If a database is not guaranteed to be available, they are set to `None`.
That is the case on the CI server.
"""

import os

import sqlalchemy as sa
from sqlalchemy import engine as engine_mod
from sqlalchemy import orm

import urban_meal_delivery


if os.getenv('TESTING'):
    # Specify the types explicitly to make mypy happy.
    engine: engine_mod.Engine = None
    connection: engine_mod.Connection = None
    session: orm.Session = None

else:  # pragma: no cover
    engine = sa.create_engine(urban_meal_delivery.config.DATABASE_URI)
    connection = engine.connect()
    session = orm.sessionmaker(bind=connection)()
