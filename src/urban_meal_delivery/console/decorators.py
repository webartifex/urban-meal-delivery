"""Utils for the CLI scripts."""

import functools
import os
import subprocess  # noqa:S404
import sys
from typing import Any, Callable

import click


def db_revision(rev: str) -> Callable:  # pragma: no cover -> easy to check visually
    """A decorator ensuring the database is at a given revision."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def ensure(*args: Any, **kwargs: Any) -> Any:  # noqa:WPS430
            """Do not execute the `func` if the revision does not match."""
            if not os.getenv('TESTING'):
                result = subprocess.run(  # noqa:S603,S607
                    ['alembic', 'current'],
                    capture_output=True,
                    check=False,
                    encoding='utf8',
                )

                if not result.stdout.startswith(rev):
                    click.echo(
                        click.style(f'Database is not at revision {rev}', fg='red'),
                    )
                    sys.exit(1)

            return func(*args, **kwargs)

        return ensure

    return decorator
