"""Utils for testing the entire package."""

import os

from urban_meal_delivery import config


if not os.getenv('TESTING'):
    raise RuntimeError('Tests must be executed with TESTING set in the environment')

if not config.TESTING:
    raise RuntimeError('The testing configuration was not loaded')
