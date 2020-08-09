"""Provide connection utils for the ORM layer."""

import sqlalchemy as sa
from sqlalchemy import engine
from sqlalchemy import orm

import urban_meal_delivery


def make_engine() -> engine.Engine:  # pragma: no cover
    """Provide a configured Engine object."""
    return sa.create_engine(urban_meal_delivery.config.DATABASE_URI)


def make_session_factory() -> orm.Session:  # pragma: no cover
    """Provide a configured Session factory."""
    return orm.sessionmaker(bind=make_engine())
