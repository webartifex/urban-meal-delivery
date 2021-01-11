"""Test the `stl()` function."""

import math

import pandas as pd
import pytest

from tests import config as test_config
from urban_meal_delivery import config
from urban_meal_delivery.forecasts import decomposition


# See remarks in `datetime_index` fixture.
FREQUENCY = 7 * 12

# The default `ns` suggested for the STL method.
NS = 7


@pytest.fixture
def datetime_index():
    """A `pd.Index` with `DateTime` values.

    The times resemble a vertical time series with a
    `frequency` of `7` times the number of daily time steps,
    which is `12` for `LONG_TIME_STEP` values.
    """
    gen = (
        start_at
        for start_at in pd.date_range(
            test_config.START, test_config.END, freq=f'{test_config.LONG_TIME_STEP}T',
        )
        if config.SERVICE_START <= start_at.hour < config.SERVICE_END
    )

    index = pd.Index(gen)
    index.name = 'start_at'

    return index


@pytest.fixture
def no_demand(datetime_index):
    """A time series of order totals when there was no demand."""
    return pd.Series(0, index=datetime_index, name='order_totals')


class TestInvalidArguments:
    """Test `stl()` with invalid arguments."""

    def test_no_nans_in_time_series(self, datetime_index):
        """`stl()` requires a `time_series` without `NaN` values."""
        time_series = pd.Series(dtype=float, index=datetime_index)

        with pytest.raises(ValueError, match='`NaN` values'):
            decomposition.stl(time_series, frequency=FREQUENCY, ns=99)

    def test_ns_not_odd(self, no_demand):
        """`ns` must be odd and `>= 7`."""
        with pytest.raises(ValueError, match='`ns`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=8)

    @pytest.mark.parametrize('ns', [-99, -1, 1, 5])
    def test_ns_smaller_than_seven(self, no_demand, ns):
        """`ns` must be odd and `>= 7`."""
        with pytest.raises(ValueError, match='`ns`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=ns)

    def test_nt_not_odd(self, no_demand):
        """`nt` must be odd and `>= default_nt`."""
        nt = 200
        default_nt = math.ceil((1.5 * FREQUENCY) / (1 - (1.5 / NS)))

        assert nt > default_nt  # sanity check

        with pytest.raises(ValueError, match='`nt`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, nt=nt)

    @pytest.mark.parametrize('nt', [-99, -1, 0, 1, 99, 159])
    def test_nt_not_at_least_the_default(self, no_demand, nt):
        """`nt` must be odd and `>= default_nt`."""
        # `default_nt` becomes 161.
        default_nt = math.ceil((1.5 * FREQUENCY) / (1 - (1.5 / NS)))

        assert nt < default_nt  # sanity check

        with pytest.raises(ValueError, match='`nt`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, nt=nt)

    def test_nl_not_odd(self, no_demand):
        """`nl` must be odd and `>= frequency`."""
        nl = 200

        assert nl > FREQUENCY  # sanity check

        with pytest.raises(ValueError, match='`nl`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, nl=nl)

    def test_nl_at_least_the_frequency(self, no_demand):
        """`nl` must be odd and `>= frequency`."""
        nl = 77

        assert nl < FREQUENCY  # sanity check

        with pytest.raises(ValueError, match='`nl`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, nl=nl)

    def test_ds_not_zero_or_one(self, no_demand):
        """`ds` must be `0` or `1`."""
        with pytest.raises(ValueError, match='`ds`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, ds=2)

    def test_dt_not_zero_or_one(self, no_demand):
        """`dt` must be `0` or `1`."""
        with pytest.raises(ValueError, match='`dt`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, dt=2)

    def test_dl_not_zero_or_one(self, no_demand):
        """`dl` must be `0` or `1`."""
        with pytest.raises(ValueError, match='`dl`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, dl=2)

    @pytest.mark.parametrize('js', [-1, 0])
    def test_js_not_positive(self, no_demand, js):
        """`js` must be positive."""
        with pytest.raises(ValueError, match='`js`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, js=js)

    @pytest.mark.parametrize('jt', [-1, 0])
    def test_jt_not_positive(self, no_demand, jt):
        """`jt` must be positive."""
        with pytest.raises(ValueError, match='`jt`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, jt=jt)

    @pytest.mark.parametrize('jl', [-1, 0])
    def test_jl_not_positive(self, no_demand, jl):
        """`jl` must be positive."""
        with pytest.raises(ValueError, match='`jl`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, jl=jl)

    @pytest.mark.parametrize('ni', [-1, 0])
    def test_ni_not_positive(self, no_demand, ni):
        """`ni` must be positive."""
        with pytest.raises(ValueError, match='`ni`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, ni=ni)

    def test_no_not_non_negative(self, no_demand):
        """`no` must be non-negative."""
        with pytest.raises(ValueError, match='`no`'):
            decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS, no=-1)


class TestValidArguments:
    """Test `stl()` with valid arguments."""

    def test_structure_of_returned_dataframe(self, no_demand):
        """`stl()` returns a `pd.DataFrame` with three columns."""
        result = decomposition.stl(no_demand, frequency=FREQUENCY, ns=NS)

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['seasonal', 'trend', 'residual']

    # Run the `stl()` function with all possible combinations of arguments,
    # including default ones and explicitly set non-default ones.
    @pytest.mark.parametrize('nt', [None, 163])
    @pytest.mark.parametrize('nl', [None, 777])
    @pytest.mark.parametrize('ds', [0, 1])
    @pytest.mark.parametrize('dt', [0, 1])
    @pytest.mark.parametrize('dl', [0, 1])
    @pytest.mark.parametrize('js', [None, 1])
    @pytest.mark.parametrize('jt', [None, 1])
    @pytest.mark.parametrize('jl', [None, 1])
    @pytest.mark.parametrize('ni', [2, 3])
    @pytest.mark.parametrize('no', [0, 1])
    def test_decompose_time_series_with_no_demand(  # noqa:WPS211,WPS216
        self, no_demand, nt, nl, ds, dt, dl, js, jt, jl, ni, no,  # noqa:WPS110
    ):
        """Decomposing a time series with no demand ...

        ... returns a `pd.DataFrame` with three columns holding only `0.0` values.
        """
        decomposed = decomposition.stl(
            no_demand,
            frequency=FREQUENCY,
            ns=NS,
            nt=nt,
            nl=nl,
            ds=ds,
            dt=dt,
            dl=dl,
            js=js,
            jt=jt,
            jl=jl,
            ni=ni,
            no=no,  # noqa:WPS110
        )

        result = decomposed.sum().sum()

        assert result == 0
