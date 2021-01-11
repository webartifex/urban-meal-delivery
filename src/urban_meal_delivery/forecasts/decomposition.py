"""Seasonal-trend decomposition procedure based on LOESS (STL).

This module defines a `stl()` function that wraps R's STL decomposition function
using the `rpy2` library.
"""

import math

import pandas as pd
from rpy2 import robjects
from rpy2.robjects import pandas2ri


def stl(  # noqa:C901,WPS210,WPS211,WPS231
    time_series: pd.Series,
    *,
    frequency: int,
    ns: int,
    nt: int = None,
    nl: int = None,
    ds: int = 0,
    dt: int = 1,
    dl: int = 1,
    js: int = None,
    jt: int = None,
    jl: int = None,
    ni: int = 2,
    no: int = 0,  # noqa:WPS110
) -> pd.DataFrame:
    """Decompose a time series into seasonal, trend, and residual components.

    This is a Python wrapper around the corresponding R function.

    Further info on the STL method:
        https://www.nniiem.ru/file/news/2016/stl-statistical-model.pdf
        https://otexts.com/fpp2/stl.html

    Further info on the R's "stl" function:
        https://www.rdocumentation.org/packages/stats/versions/3.6.2/topics/stl

    Args:
        time_series: time series with a `DateTime` based index;
            must not contain `NaN` values
        frequency: frequency of the observations in the `time_series`
        ns: smoothing parameter for the seasonal component
            (= window size of the seasonal smoother);
            must be odd and `>= 7` so that the seasonal component is smooth;
            the greater `ns`, the smoother the seasonal component;
            so, this is a hyper-parameter optimized in accordance with the application
        nt: smoothing parameter for the trend component
            (= window size of the trend smoother);
            must be odd and `>= (1.5 * frequency) / [1 - (1.5 / ns)]`;
            the latter threshold is the default value;
            the greater `nt`, the smoother the trend component
        nl: smoothing parameter for the low-pass filter;
            must be odd and `>= frequency`;
            the least odd number `>= frequency` is the default
        ds: degree of locally fitted polynomial in seasonal smoothing;
            must be `0` or `1`
        dt: degree of locally fitted polynomial in trend smoothing;
            must be `0` or `1`
        dl: degree of locally fitted polynomial in low-pass smoothing;
            must be `0` or `1`
        js: number of steps by which the seasonal smoother skips ahead
            and then linearly interpolates between observations;
            if set to `1`, the smoother is evaluated at all points;
            to make the STL decomposition faster, increase this value;
            by default, `js` is the smallest integer `>= 0.1 * ns`
        jt: number of steps by which the trend smoother skips ahead
            and then linearly interpolates between observations;
            if set to `1`, the smoother is evaluated at all points;
            to make the STL decomposition faster, increase this value;
            by default, `jt` is the smallest integer `>= 0.1 * nt`
        jl: number of steps by which the low-pass smoother skips ahead
            and then linearly interpolates between observations;
            if set to `1`, the smoother is evaluated at all points;
            to make the STL decomposition faster, increase this value;
            by default, `jl` is the smallest integer `>= 0.1 * nl`
        ni: number of iterations of the inner loop that updates the
            seasonal and trend components;
            usually, a low value (e.g., `2`) suffices
        no: number of iterations of the outer loop that handles outliers;
            also known as the "robustness" loop;
            if no outliers need to be handled, set `no=0`;
            otherwise, `no=5` or `no=10` combined with `ni=1` is a good choice

    Returns:
        result: a DataFrame with three columns ("seasonal", "trend", and "residual")
            providing time series of the individual components

    Raises:
        ValueError: some argument does not adhere to the specifications above
    """
    # Re-seed R every time the process does something.
    robjects.r('set.seed(42)')

    # Validate all arguments and set default values.

    if time_series.isnull().any():
        raise ValueError('`time_series` must not contain `NaN` values')

    if ns % 2 == 0 or ns < 7:
        raise ValueError('`ns` must be odd and `>= 7`')

    default_nt = math.ceil((1.5 * frequency) / (1 - (1.5 / ns)))  # noqa:WPS432
    if nt is not None:
        if nt % 2 == 0 or nt < default_nt:
            raise ValueError(
                '`nt` must be odd and `>= (1.5 * frequency) / [1 - (1.5 / ns)]`, '
                + 'which is {0}'.format(default_nt),
            )
    else:
        nt = default_nt
        if nt % 2 == 0:  # pragma: no cover => hard to construct edge case
            nt += 1

    if nl is not None:
        if nl % 2 == 0 or nl < frequency:
            raise ValueError('`nl` must be odd and `>= frequency`')
    elif frequency % 2 == 0:
        nl = frequency + 1
    else:  # pragma: no cover => hard to construct edge case
        nl = frequency

    if ds not in {0, 1}:
        raise ValueError('`ds` must be either `0` or `1`')
    if dt not in {0, 1}:
        raise ValueError('`dt` must be either `0` or `1`')
    if dl not in {0, 1}:
        raise ValueError('`dl` must be either `0` or `1`')

    if js is not None:
        if js <= 0:
            raise ValueError('`js` must be positive')
    else:
        js = math.ceil(ns / 10)

    if jt is not None:
        if jt <= 0:
            raise ValueError('`jt` must be positive')
    else:
        jt = math.ceil(nt / 10)

    if jl is not None:
        if jl <= 0:
            raise ValueError('`jl` must be positive')
    else:
        jl = math.ceil(nl / 10)

    if ni <= 0:
        raise ValueError('`ni` must be positive')

    if no < 0:
        raise ValueError('`no` must be non-negative')
    elif no > 0:
        robust = True
    else:
        robust = False

    # Call the STL function in R.
    ts = robjects.r['ts'](pandas2ri.py2rpy(time_series), frequency=frequency)
    result = robjects.r['stl'](
        ts, ns, ds, nt, dt, nl, dl, js, jt, jl, robust, ni, no,  # noqa:WPS221
    )

    # Unpack the result to a `pd.DataFrame`.
    result = pandas2ri.rpy2py(result[0])
    result = {
        'seasonal': pd.Series(result[:, 0], index=time_series.index),
        'trend': pd.Series(result[:, 1], index=time_series.index),
        'residual': pd.Series(result[:, 2], index=time_series.index),
    }

    return pd.DataFrame(result)
