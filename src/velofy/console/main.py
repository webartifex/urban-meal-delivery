"""The entry point for all CLI scripts in the project."""

from typing import Any

import click
from click import core as cli_core

import velofy


def show_version(ctx: cli_core.Context, _param: Any, value: bool) -> None:
    """Show the package's version."""
    # If --version / -V is NOT passed in,
    # continue with the command.
    if not value or ctx.resilient_parsing:
        return

    # Mimic the colors of `poetry version`.
    pkg_name = click.style(velofy.__pkg_name__, fg='green')
    version = click.style(velofy.__version__, fg='blue')
    # Include a warning for development versions.
    warning = click.style(' (development)', fg='red') if '.dev' in version else ''
    click.echo(f'{pkg_name}, version {version}{warning}')
    ctx.exit()


@click.group()
@click.option(
    '--version',
    '-V',
    is_flag=True,
    callback=show_version,
    is_eager=True,
    expose_value=False,
)
def entry_point() -> None:
    """The velofy research project."""
