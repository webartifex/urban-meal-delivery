"""Fixture for testing the CLI scripts."""

import pytest
from click import testing as click_testing


@pytest.fixture
def cli() -> click_testing.CliRunner:
    """Initialize Click's CLI Test Runner."""
    return click_testing.CliRunner()
