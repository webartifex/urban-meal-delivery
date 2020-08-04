"""Source code for the urban-meal-delivery research project."""

from importlib import metadata as _metadata


try:
    _pkg_info = _metadata.metadata(__name__)

except _metadata.PackageNotFoundError:  # pragma: no cover
    __pkg_name__ = 'unknown'
    __version__ = 'unknown'

else:
    __pkg_name__ = _pkg_info['name']
    __version__ = _pkg_info['version']
