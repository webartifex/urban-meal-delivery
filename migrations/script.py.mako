"""${message}.

Revision: # ${up_revision} at ${create_date}
Revises: # ${down_revision | comma,n}
"""

import os

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

from urban_meal_delivery import configuration

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision ${up_revision}."""
    ${upgrades if upgrades else "pass"}


def downgrade():
    """Downgrade to revision ${down_revision}."""
    ${downgrades if downgrades else "pass"}
