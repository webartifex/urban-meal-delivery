"""Globals used when testing."""

import datetime

from urban_meal_delivery import config


# The day on which most test cases take place.
YEAR, MONTH, DAY = 2016, 7, 1

# The hour when most test cases take place.
NOON = 12

# `START` and `END` constitute a 22-day time span.
# That implies a maximum `train_horizon` of `3` as that needs full 7-day weeks.
START = datetime.datetime(YEAR, MONTH, DAY, config.SERVICE_START, 0)
END = datetime.datetime(YEAR, MONTH, DAY + 21, config.SERVICE_END, 0)

# Default time steps (in minutes), for example, for `OrderHistory` objects.
LONG_TIME_STEP = 60
SHORT_TIME_STEP = 30
TIME_STEPS = (SHORT_TIME_STEP, LONG_TIME_STEP)
# The `frequency` of vertical time series is the number of days in a week, 7,
# times the number of time steps per day. With 12 operating hours (11 am - 11 pm)
# the `frequency`s are 84 and 168 for the `LONG/SHORT_TIME_STEP`s.
VERTICAL_FREQUENCY_LONG = 7 * 12
VERTICAL_FREQUENCY_SHORT = 7 * 24

# Default training horizons, for example, for
# `OrderHistory.make_horizontal_time_series()`.
LONG_TRAIN_HORIZON = 3
SHORT_TRAIN_HORIZON = 2
TRAIN_HORIZONS = (SHORT_TRAIN_HORIZON, LONG_TRAIN_HORIZON)
