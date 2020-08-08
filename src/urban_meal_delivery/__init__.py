"""Source code for the urban-meal-delivery research project.

Example:
    >>> import urban_meal_delivery as umd
    >>> umd.__version__ != '0.0.0'
    True
"""

import os as _os
from importlib import metadata as _metadata

from urban_meal_delivery import _config  # noqa:WPS450


try:
    _pkg_info = _metadata.metadata(__name__)

except _metadata.PackageNotFoundError:  # pragma: no cover
    __author__ = 'unknown'
    __pkg_name__ = 'unknown'
    __version__ = 'unknown'

else:
    __author__ = _pkg_info['author']
    __pkg_name__ = _pkg_info['name']
    __version__ = _pkg_info['version']


# Little Hack: "Overwrites" the config module so that the environment is already set.
config = _config.get_config('testing' if _os.getenv('TESTING') else 'production')
