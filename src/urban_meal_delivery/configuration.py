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


def random_schema_name() -> str:
    """Generate a random PostgreSQL schema name for testing."""
    return 'temp_{name}'.format(
        name=''.join(
            (random.choice(string.ascii_lowercase) for _ in range(10)),  # noqa:S311
        ),
    )


class Config:
    """Configuration that applies in all situations."""

    # Application-specific settings
    # -----------------------------

    # Date after which the real-life data is discarded.
    CUTOFF_DAY = datetime.datetime(2017, 2, 1)

    # If a scheduled pre-order is made within this
    # time horizon, we treat it as an ad-hoc order.
    QUASI_AD_HOC_LIMIT = datetime.timedelta(minutes=45)

    # Operating hours of the platform.
    SERVICE_START = 11
    SERVICE_END = 23

    # Side lengths (in meters) for which pixel grids are created.
    # They are the basis for the aggregated demand forecasts.
    GRID_SIDE_LENGTHS = [707, 1000, 1414]

    # Time steps (in minutes) used to aggregate the
    # individual orders into time series.
    TIME_STEPS = [60]

    # Training horizons (in full weeks) used
    # to train the forecasting models.
    TRAINING_HORIZONS = [8]

    # The demand forecasting methods used in the simulations.
    FORECASTING_METHODS = ['hets', 'rtarima']

    # Implementation-specific settings
    # --------------------------------

    DATABASE_URI = os.getenv('DATABASE_URI')

    # The PostgreSQL schema that holds the tables with the original data.
    ORIGINAL_SCHEMA = os.getenv('ORIGINAL_SCHEMA') or 'public'

    # The PostgreSQL schema that holds the tables with the cleaned data.
    CLEAN_SCHEMA = os.getenv('CLEAN_SCHEMA') or 'clean'

    ALEMBIC_TABLE = 'alembic_version'
    ALEMBIC_TABLE_SCHEMA = 'public'

    R_LIBS_PATH = os.getenv('R_LIBS')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<configuration>'


class ProductionConfig(Config):
    """Configuration for the real dataset."""

    TESTING = False


class TestingConfig(Config):
    """Configuration for the test suite."""

    TESTING = True

    DATABASE_URI = os.getenv('DATABASE_URI_TESTING') or Config.DATABASE_URI
    CLEAN_SCHEMA = os.getenv('CLEAN_SCHEMA_TESTING') or random_schema_name()


def make_config(env: str = 'production') -> Config:
    """Create a new `Config` object.

    Args:
        env: either 'production' or 'testing'

    Returns:
        config: a namespace with all configurations

    Raises:
        ValueError: if `env` is not as specified
    """  # noqa:DAR203
    config: Config  # otherwise mypy is confused

    if env.strip().lower() == 'production':
        config = ProductionConfig()
    elif env.strip().lower() == 'testing':
        config = TestingConfig()
    else:
        raise ValueError("Must be either 'production' or 'testing'")

    # Without a PostgreSQL database the package cannot work.
    # As pytest sets the "TESTING" environment variable explicitly,
    # the warning is only emitted if the code is not run by pytest.
    # We see the bad configuration immediately as all "db" tests fail.
    if config.DATABASE_URI is None and not os.getenv('TESTING'):
        warnings.warn('Bad configurartion: no DATABASE_URI set in the environment')

    # Some functionalities require R and some packages installed.
    # To ensure isolation and reproducibility, the projects keeps the R dependencies
    # in a project-local folder that must be set in the environment.
    if config.R_LIBS_PATH is None and not os.getenv('TESTING'):
        warnings.warn('Bad configuration: no R_LIBS set in the environment')

    return config


config = make_config('testing' if os.getenv('TESTING') else 'production')
