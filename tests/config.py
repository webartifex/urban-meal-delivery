"""Globals used when testing."""

import datetime

from urban_meal_delivery import config


# The day on which most test cases take place.
YEAR, MONTH, DAY = 2016, 7, 1

# The hour when most test cases take place.
NOON = 12

# `START` and `END` constitute a 15-day time span.
# That implies a maximum `train_horizon` of `2` as that needs full 7-day weeks.
START = datetime.datetime(YEAR, MONTH, DAY, config.SERVICE_START, 0)
END = datetime.datetime(YEAR, MONTH, 15, config.SERVICE_END, 0)

# Default time steps, for example, for `OrderHistory` objects.
LONG_TIME_STEP = 60
SHORT_TIME_STEP = 30
TIME_STEPS = (SHORT_TIME_STEP, LONG_TIME_STEP)

# Default training horizons, for example, for
# `OrderHistory.make_horizontal_time_series()`.
LONG_TRAIN_HORIZON = 2
SHORT_TRAIN_HORIZON = 1
TRAIN_HORIZONS = (SHORT_TRAIN_HORIZON, LONG_TRAIN_HORIZON)
