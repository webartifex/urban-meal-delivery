"""Configure nox for the isolated test and lint environments."""

import os
import tempfile
from typing import Any

import nox
from nox.sessions import Session


MAIN_PYTHON = '3.8'

# Keep the project is forward compatible.
NEXT_PYTHON = '3.9'

# Paths with *.py files.
SRC_LOCATIONS = 'noxfile.py', 'src/'


# Use a unified .cache/ folder for all tools.
nox.options.envdir = '.cache/nox'

# All tools except git and poetry are project dependencies.
# Avoid accidental successes if the environment is not set up properly.
nox.options.error_on_external_run = True

# Run only CI related checks by default.
nox.options.sessions = (
    'format',
    'lint',
    f'test-{MAIN_PYTHON}',
    f'test-{NEXT_PYTHON}',
)


@nox.session(name='format', python=MAIN_PYTHON)
def format_(session: Session):
    """Format source files."""
    _begin(session)


@nox.session(python=MAIN_PYTHON)
def lint(session: Session):
    """Lint source files."""
    _begin(session)


@nox.session(python=[MAIN_PYTHON, NEXT_PYTHON])
def test(session: Session):
    """Test the code base."""
    _begin(session)


@nox.session(name='pre-commit', python=MAIN_PYTHON, venv_backend='none')
def pre_commit(session: Session):
    """Source files must be well-formed before they enter git."""
    _begin(session)
    session.notify('format')
    session.notify('lint')


@nox.session(name='pre-merge', python=MAIN_PYTHON, venv_backend='none')
def pre_merge(session: Session):
    """The test suite must pass before merges are made."""
    _begin(session)
    session.notify('test')


def _begin(session: Session) -> None:
    """Show generic info about a session."""
    if session.posargs:
        print('extra arguments:', *session.posargs)

    session.run('python', '--version')

    # Fake GNU's pwd.
    session.log('pwd')
    print(os.getcwd())


def _install_packages(
    session: Session, *packages_or_pip_args: str, **kwargs: Any
) -> None:
    """Install packages respecting the poetry.lock file.

    This function wraps nox.sessions.Session.install() such that it installs
    packages respecting the pinnned versions specified in poetry's lock file.
    This makes nox sessions even more deterministic.

    Args:
        session: the Session object
        *packages_or_pip_args: the packages to be installed or pip options
        **kwargs: passed on to nox.sessions.Session.install()
    """
    if session.virtualenv.reuse_existing:
        session.log(
            'No dependencies are installed as an existing environment is re-used',
        )
        return

    session.log('Dependencies are installed respecting the poetry.lock file')

    with tempfile.NamedTemporaryFile() as requirements_txt:
        session.run(
            'poetry',
            'export',
            '--dev',
            '--format=requirements.txt',
            f'--output={requirements_txt.name}',
            external=True,
        )
        session.install(
            f'--constraint={requirements_txt.name}', *packages_or_pip_args, **kwargs,
        )
