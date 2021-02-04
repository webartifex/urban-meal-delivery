"""Demand forecasting utilities.

This sub-package is divided into further sub-packages and modules as follows:

`methods` contains various time series related statistical methods, implemented
as plain `function` objects that are used to predict into the future given a
time series of historic order counts. The methods are context-agnostic, meaning
that they only take and return `pd.Series/DataFrame`s holding numbers and
are not concerned with how these numbers were generated or what they mean.
Some functions, like `arima.predict()` or `ets.predict()` wrap functions called
in R using the `rpy2` library. Others, like `extrapolate_season.predict()`, are
written in plain Python.

`timify` defines an `OrderHistory` class that abstracts away the communication
with the database and provides `pd.Series` objects with the order counts that
are fed into the `methods`. In particular, it uses SQL statements behind the
scenes to calculate the historic order counts on a per-`Pixel` level. Once the
data is loaded from the database, an `OrderHistory` instance provides various
ways to slice out, or generate, different kinds of order time series (e.g.,
"horizontal" vs. "vertical" time series).

`models` defines various forecasting `*Model`s that combine a given kind of
time series with one of the forecasting `methods`. For example, the ETS method
applied to a horizontal time series is implemented in the `HorizontalETSModel`.
"""

from urban_meal_delivery.forecasts import methods
from urban_meal_delivery.forecasts import models
from urban_meal_delivery.forecasts import timify
