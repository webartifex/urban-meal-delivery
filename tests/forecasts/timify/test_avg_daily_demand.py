"""Tests for the `OrderHistory.avg_daily_demand()` and ...

`OrderHistory.choose_tactical_model()` methods.

We test both methods together as they take the same input and are really
two parts of the same conceptual step.
"""

import pytest

from tests import config as test_config
from urban_meal_delivery.forecasts import models


class TestAverageDailyDemand:
    """Tests for the `OrderHistory.avg_daily_demand()` method."""

    def test_avg_daily_demand_with_constant_demand(
        self, order_history, good_pixel_id, predict_at,
    ):
        """The average daily demand must be the number of time steps ...

        ... if the demand is `1` at each time step.

        Note: The `order_history` fixture assumes `12` time steps per day as it
        uses `LONG_TIME_STEP=60` as the length of a time step.
        """
        result = order_history.avg_daily_demand(
            pixel_id=good_pixel_id,
            predict_day=predict_at.date(),
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert result == 12.0

    def test_avg_daily_demand_with_no_demand(
        self, order_history, good_pixel_id, predict_at,
    ):
        """Without demand, the average daily demand must be `0.0`."""
        order_history._data.loc[:, 'n_orders'] = 0

        result = order_history.avg_daily_demand(
            pixel_id=good_pixel_id,
            predict_day=predict_at.date(),
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert result == 0.0


class TestChooseTacticalModel:
    """Tests for the `OrderHistory.choose_tactical_model()` method."""

    def test_best_model_with_high_demand(
        self, order_history, good_pixel_id, predict_at,
    ):
        """With high demand, the average daily demand is `.>= 25.0`."""
        # With 12 time steps per day, the ADD becomes `36.0`.
        order_history._data.loc[:, 'n_orders'] = 3

        result = order_history.choose_tactical_model(
            pixel_id=good_pixel_id,
            predict_day=predict_at.date(),
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert isinstance(result, models.HorizontalETSModel)

    def test_best_model_with_medium_demand(
        self, order_history, good_pixel_id, predict_at,
    ):
        """With medium demand, the average daily demand is `>= 10.0` and `< 25.0`."""
        # With 12 time steps per day, the ADD becomes `24.0`.
        order_history._data.loc[:, 'n_orders'] = 2

        result = order_history.choose_tactical_model(
            pixel_id=good_pixel_id,
            predict_day=predict_at.date(),
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        assert isinstance(result, models.HorizontalETSModel)

    def test_best_model_with_low_demand(
        self, order_history, good_pixel_id, predict_at,
    ):
        """With low demand, the average daily demand is `>= 2.5` and `< 10.0`."""
        # With 12 time steps per day, the ADD becomes `12.0` ...
        data = order_history._data
        data.loc[:, 'n_orders'] = 1

        # ... and we set three additional time steps per day to `0`.
        data.loc[  # noqa:ECE001
            # all `Pixel`s, all `Order`s in time steps starting at 11 am
            (slice(None), slice(data.index.levels[1][0], None, 12)),
            'n_orders',
        ] = 0
        data.loc[  # noqa:ECE001
            # all `Pixel`s, all `Order`s in time steps starting at 12 am
            (slice(None), slice(data.index.levels[1][1], None, 12)),
            'n_orders',
        ] = 0
        data.loc[  # noqa:ECE001
            # all `Pixel`s, all `Order`s in time steps starting at 1 pm
            (slice(None), slice(data.index.levels[1][2], None, 12)),
            'n_orders',
        ] = 0

        result = order_history.choose_tactical_model(
            pixel_id=good_pixel_id,
            predict_day=predict_at.date(),
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        # TODO: this should be the future `HorizontalSMAModel`.
        assert isinstance(result, models.HorizontalETSModel)

    def test_best_model_with_no_demand(
        self, order_history, good_pixel_id, predict_at,
    ):
        """Without demand, the average daily demand is `< 2.5`."""
        order_history._data.loc[:, 'n_orders'] = 0

        result = order_history.choose_tactical_model(
            pixel_id=good_pixel_id,
            predict_day=predict_at.date(),
            train_horizon=test_config.LONG_TRAIN_HORIZON,
        )

        # TODO: this should be the future `HorizontalTrivialModel`.
        assert isinstance(result, models.HorizontalETSModel)

    def test_best_model_for_unknown_train_horizon(
        self, order_history, good_pixel_id, predict_at,  # noqa:RST215
    ):
        """For `train_horizon`s not included in the rule-based system ...

        ... the method raises a `RuntimeError`.
        """
        with pytest.raises(RuntimeError, match='no rule'):
            order_history.choose_tactical_model(
                pixel_id=good_pixel_id,
                predict_day=predict_at.date(),
                train_horizon=test_config.SHORT_TRAIN_HORIZON,
            )
