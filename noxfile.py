"""Configure nox for the isolated test and lint environments."""

import contextlib
import os
import tempfile
from typing import Any, Generator

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
def format_(session: Session) -> None:
    """Format source files with autoflake, black, and isort."""
    _begin(session)
    _install_packages(session, 'autoflake', 'black', 'isort')
    # Interpret extra arguments as locations of source files.
    locations = session.posargs or SRC_LOCATIONS
    session.run('autoflake', '--version')
    session.run(
        'autoflake',
        '--in-place',
        '--recursive',
        '--expand-star-imports',
        '--remove-all-unused-imports',
        '--ignore-init-module-imports',  # modifies --remove-all-unused-imports
        '--remove-duplicate-keys',
        '--remove-unused-variables',
        *locations,
    )
    session.run('black', '--version')
    session.run('black', *locations)
    with _isort_fix(session):  # TODO (isort): Remove after upgrading
        session.run('isort', '--version')
        session.run('isort', *locations)


@nox.session(python=MAIN_PYTHON)
def lint(session: Session) -> None:
    """Lint source files with flake8, mypy, and pylint."""
    _begin(session)
    _install_packages(
        session,
        'flake8',
        'flake8-annotations',
        'flake8-black',
        'flake8-expression-complexity',
        'mypy',
        'pylint',
        'wemake-python-styleguide',
    )
    # Interpret extra arguments as locations of source files.
    locations = session.posargs or SRC_LOCATIONS
    session.run('flake8', '--version')
    session.run('flake8', '--ignore=I0', *locations)  # TODO (isort): Remove flag
    with _isort_fix(session):  # TODO (isort): Remove after upgrading
        session.run('isort', '--version')
        session.run('isort', '--check-only', *locations)
    session.run('mypy', '--version')
    session.run('mypy', *locations)
    # Ignore errors where pylint cannot import a third-party package due its
    # being run in an isolated environment. One way to fix this is to install
    # all develop dependencies in this nox session, which we do not do. The
    # whole point of static linting tools is to not rely on any package be
    # importable at runtime. Instead, these imports are validated implicitly
    # when the test suite is run.
    session.run('pylint', '--version')
    session.run('pylint', '--disable=import-error', *locations)


@nox.session(python=[MAIN_PYTHON, NEXT_PYTHON])
def test(session: Session) -> None:
    """Test the code base."""
    _begin(session)


@nox.session(name='pre-commit', python=MAIN_PYTHON, venv_backend='none')
def pre_commit(session: Session) -> None:
    """Source files must be well-formed before they enter git."""
    _begin(session)
    session.notify('format')
    session.notify('lint')


@nox.session(name='pre-merge', python=MAIN_PYTHON, venv_backend='none')
def pre_merge(session: Session) -> None:
    """The test suite must pass before merges are made."""
    _begin(session)
    session.notify('test')


def _begin(session: Session) -> None:
    """Show generic info about a session."""
    if session.posargs:
        print('extra arguments:', *session.posargs)  # noqa:WPS421

    session.run('python', '--version')

    # Fake GNU's pwd.
    session.log('pwd')
    print(os.getcwd())  # noqa:WPS421


def _install_packages(
    session: Session, *packages_or_pip_args: str, **kwargs: Any,
) -> None:
    """Install packages respecting the poetry.lock file.

    This function wraps nox.sessions.Session.install() such that it installs
    packages respecting the pinnned versions specified in poetry's lock file.
    This makes nox sessions even more deterministic.

    Args:
        session: the Session object
        *packages_or_pip_args: the packages to be installed or pip options
        **kwargs: passed on to nox.sessions.Session.install()
    """  # noqa:RST210,RST213
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


# TODO (isort): Remove this fix after
# upgrading to isort ^5.2.2 in pyproject.toml.
@contextlib.contextmanager
def _isort_fix(session: Session) -> Generator:
    """Temporarily upgrade to isort 5.2.2."""
    session.install('isort==5.2.2')
    try:
        yield
    finally:
        session.install('isort==4.3.21')
