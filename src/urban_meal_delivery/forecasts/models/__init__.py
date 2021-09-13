"""Define the forecasting `*Model`s used in this project.

`*Model`s are different from plain forecasting `methods` in that they are tied
to a given kind of historic order time series, as provided by the `OrderHistory`
class in the `timify` module. For example, the ARIMA model applied to a vertical
time series becomes the `VerticalARIMAModel`.

An overview of the `*Model`s used for tactical forecasting can be found in section
"3.6 Forecasting Models" in the paper "Real-time Demand Forecasting for an Urban
Delivery Platform" that is part of the `urban-meal-delivery` research project.

For the paper check:
    https://github.com/webartifex/urban-meal-delivery-demand-forecasting/blob/main/paper.pdf
    https://www.sciencedirect.com/science/article/pii/S1366554520307936

This sub-package is organized as follows. The `base` module defines an abstract
`ForecastingModelABC` class that unifies how the concrete `*Model`s work.
While the abstract `.predict()` method returns a `pd.DataFrame` (= basically,
the result of one of the forecasting `methods`, the concrete `.make_forecast()`
method converts the results into `Forecast` (=ORM) objects.
Also, `.make_forecast()` implements a caching strategy where already made
`Forecast`s are loaded from the database instead of calculating them again,
which could be a heavier computation.

The `tactical` sub-package contains all the `*Model`s used to implement the
predictive routing strategy employed by the UDP.

A future `planning` sub-package will contain the `*Model`s used to plan the
`Courier`'s shifts a week ahead.
"""  # noqa:RST215

from urban_meal_delivery.forecasts.models.base import ForecastingModelABC
from urban_meal_delivery.forecasts.models.tactical.horizontal import HorizontalETSModel
from urban_meal_delivery.forecasts.models.tactical.horizontal import HorizontalSMAModel
from urban_meal_delivery.forecasts.models.tactical.other import TrivialModel
from urban_meal_delivery.forecasts.models.tactical.realtime import RealtimeARIMAModel
from urban_meal_delivery.forecasts.models.tactical.vertical import VerticalARIMAModel
