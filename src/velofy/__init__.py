"""Source code for the urban-meal-delivery research project.

Example:
    >>> import velofy
    >>> velofy.__version__ != '0.0.0'
    True
"""
# The config object must come before all other project-internal imports.
from velofy.configuration import config  # isort:skip

from importlib import metadata as _metadata

from velofy import db
from velofy import forecasts


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
