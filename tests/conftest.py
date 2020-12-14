"""Utils for testing the entire package."""

import os

from urban_meal_delivery import config


# The TESTING environment variable is set
# in setup.cfg in pytest's config section.
if not os.getenv('TESTING'):
    raise RuntimeError('Tests must be executed with TESTING set in the environment')

if not config.TESTING:
    raise RuntimeError('The testing configuration was not loaded')
