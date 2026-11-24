"""Verify that the R packages are installed correctly."""

import pytest


@pytest.mark.r
def test_r_packages_installed():
    """Import the `velofy.init_r` module.

    Doing this raises a `PackageNotInstalledError` if the
    mentioned R packages are not importable.

    They must be installed externally. That happens either
    in the "research/r_dependencies.ipynb" notebook or
    in the GitHub Actions CI.
    """
    from velofy import init_r  # noqa:WPS433

    assert init_r is not None
