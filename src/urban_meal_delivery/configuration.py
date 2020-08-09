"""Provide package-wide configuration.

This module provides utils to create new `Config` objects
on the fly, mainly for testing and migrating!

Within this package, use the `config` proxy at the package's top level
to access the current configuration!
"""

import datetime
import os
import random
import string
import warnings

import dotenv


dotenv.load_dotenv()


def random_schema_name() -> str:
    """Generate a random PostgreSQL schema name for testing."""
    return 'temp_{name}'.format(
        name=''.join(
            (random.choice(string.ascii_lowercase) for _ in range(10)),  # noqa:S311
        ),
    )


class Config:
    """Configuration that applies in all situations."""

    # pylint:disable=too-few-public-methods

    CUTOFF_DAY = datetime.datetime(2017, 2, 1)

    # If a scheduled pre-order is made within this
    # time horizon, we treat it as an ad-hoc order.
    QUASI_AD_HOC_LIMIT = datetime.timedelta(minutes=45)

    DATABASE_URI = os.getenv('DATABASE_URI')

    # The PostgreSQL schema that holds the tables with the original data.
    ORIGINAL_SCHEMA = os.getenv('ORIGINAL_SCHEMA') or 'public'

    # The PostgreSQL schema that holds the tables with the cleaned data.
    CLEAN_SCHEMA = os.getenv('CLEAN_SCHEMA') or 'clean'

    ALEMBIC_TABLE = 'alembic_version'
    ALEMBIC_TABLE_SCHEMA = 'public'

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<configuration>'


class ProductionConfig(Config):
    """Configuration for the real dataset."""

    # pylint:disable=too-few-public-methods

    TESTING = False


class TestingConfig(Config):
    """Configuration for the test suite."""

    # pylint:disable=too-few-public-methods

    TESTING = True

    DATABASE_URI = os.getenv('DATABASE_URI_TESTING') or Config.DATABASE_URI
    CLEAN_SCHEMA = os.getenv('CLEAN_SCHEMA_TESTING') or random_schema_name()


def make_config(env: str = 'production') -> Config:
    """Create a new `Config` object.

    Args:
        env: either 'production' or 'testing'; defaults to the first

    Returns:
        config: a namespace with all configurations

    Raises:
        ValueError: if `env` is not as specified
    """  # noqa:DAR203
    config: Config
    if env.strip().lower() == 'production':
        config = ProductionConfig()
    elif env.strip().lower() == 'testing':
        config = TestingConfig()
    else:
        raise ValueError("Must be either 'production' or 'testing'")

    # Without a PostgreSQL database the package cannot work.
    if config.DATABASE_URI is None:
        warnings.warn('Bad configurartion: no DATABASE_URI set in the environment')

    return config
