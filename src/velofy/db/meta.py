"""Provide the ORM's declarative base."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy import orm

import velofy


Base: Any = orm.declarative_base(
    metadata=sa.MetaData(
        schema=velofy.config.CLEAN_SCHEMA,
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_to_%(referred_table_name)s_via_%(column_0_N_name)s",  # noqa:E501
            "uq": "uq_%(table_name)s_on_%(column_0_N_name)s",
            "ix": "ix_%(table_name)s_on_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_on_%(constraint_name)s",
        },
    ),
)
