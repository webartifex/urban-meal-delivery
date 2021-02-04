"""Globals used when testing."""

import datetime as dt

from urban_meal_delivery import config


# The day on which most test cases take place.
YEAR, MONTH, DAY = 2016, 7, 1

# The hour when most test cases take place.
NOON = 12

# `START` and `END` constitute a 57-day time span, 8 full weeks plus 1 day.
# That implies a maximum `train_horizon` of `8` as that needs full 7-day weeks.
START = dt.datetime(YEAR, MONTH, DAY, config.SERVICE_START, 0)
_end = START + dt.timedelta(days=56)  # `56` as `START` is not included
END = dt.datetime(_end.year, _end.month, _end.day, config.SERVICE_END, 0)

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
LONG_TRAIN_HORIZON = 8
SHORT_TRAIN_HORIZON = 2
TRAIN_HORIZONS = (SHORT_TRAIN_HORIZON, LONG_TRAIN_HORIZON)
