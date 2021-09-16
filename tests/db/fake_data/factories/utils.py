"""Utilities used in all `*Factory` classes."""

import datetime as dt
import random

from tests import config as test_config


def random_timespan(  # noqa:WPS211
    *,
    min_hours=0,
    min_minutes=0,
    min_seconds=0,
    max_hours=0,
    max_minutes=0,
    max_seconds=0,
):
    """A randomized `timedelta` object between the specified arguments."""
    total_min_seconds = min_hours * 3600 + min_minutes * 60 + min_seconds
    total_max_seconds = max_hours * 3600 + max_minutes * 60 + max_seconds
    return dt.timedelta(seconds=random.randint(total_min_seconds, total_max_seconds))


def early_in_the_morning():
    """A randomized `datetime` object early in the morning."""
    early = dt.datetime(*test_config.DATE, 3, 0)
    return early + random_timespan(max_hours=2)
