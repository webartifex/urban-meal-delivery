"""Provide the ORM's declarative base."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext import declarative

import urban_meal_delivery


Base: Any = declarative.declarative_base(
    metadata=sa.MetaData(
        schema=urban_meal_delivery.config.CLEAN_SCHEMA,
        naming_convention={
            'pk': 'pk_%(table_name)s',  # noqa:WPS323
            'fk': 'fk_%(table_name)s_to_%(referred_table_name)s_via_%(column_0_N_name)s',  # noqa:E501,WPS323
            'uq': 'uq_%(table_name)s_on_%(column_0_N_name)s',  # noqa:WPS323
            'ix': 'ix_%(table_name)s_on_%(column_0_N_name)s',  # noqa:WPS323
            'ck': 'ck_%(table_name)s_on_%(constraint_name)s',  # noqa:WPS323
        },
    ),
)
