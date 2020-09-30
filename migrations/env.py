"""Configure Alembic's migration environment."""

import os
from logging import config as log_config

import sqlalchemy as sa
from alembic import context

from urban_meal_delivery import config as umd_config
from urban_meal_delivery import db


# Disable the --sql option, a.k.a, the "offline mode".
if context.is_offline_mode():
    raise NotImplementedError('The --sql option is not implemented in this project')


# Set up the default Python logger from the alembic.ini file.
log_config.fileConfig(context.config.config_file_name)


def include_object(obj, _name, type_, _reflected, _compare_to):
    """Only include the clean schema into --autogenerate migrations."""
    if type_ in {'table', 'column'} and obj.schema != umd_config.DATABASE_SCHEMA:
        return False

    return True


engine = sa.create_engine(umd_config.DATABASE_URI)

with engine.connect() as connection:
    context.configure(
        connection=connection,
        include_object=include_object,
        target_metadata=db.Base.metadata,
        version_table='{alembic_table}{test_schema}'.format(
            alembic_table=umd_config.ALEMBIC_TABLE,
            test_schema=(f'_{umd_config.CLEAN_SCHEMA}' if os.getenv('TESTING') else ''),
        ),
        version_table_schema=umd_config.ALEMBIC_TABLE_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()
