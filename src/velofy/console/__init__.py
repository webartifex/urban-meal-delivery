"""Provide CLI scripts for the project."""

from velofy.console import forecasts
from velofy.console import gridify
from velofy.console import main


cli = main.entry_point

cli.add_command(forecasts.tactical_heuristic, name="tactical-forecasts")
cli.add_command(gridify.gridify)
