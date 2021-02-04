"""Provide CLI scripts for the project."""

from urban_meal_delivery.console import forecasts
from urban_meal_delivery.console import gridify
from urban_meal_delivery.console import main


cli = main.entry_point

cli.add_command(forecasts.tactical_heuristic, name='tactical-forecasts')
cli.add_command(gridify.gridify)
