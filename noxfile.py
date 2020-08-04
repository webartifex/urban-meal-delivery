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

# Path to the test suite.
PYTEST_LOCATION = 'tests/'

# Paths with *.py files.
SRC_LOCATIONS = 'noxfile.py', 'src/', PYTEST_LOCATION


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
    """Format source files with autoflake, black, and isort.

    If no extra arguments are provided, all source files are formatted.
    Otherwise, they are interpreted as paths the formatters work on recursively.
    """
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
    """Lint source files with flake8, mypy, and pylint.

    If no extra arguments are provided, all source files are linted.
    Otherwise, they are interpreted as paths the linters work on recursively.
    """
    _begin(session)
    _install_packages(
        session,
        'flake8',
        'flake8-annotations',
        'flake8-black',
        'flake8-expression-complexity',
        'flake8-pytest-style',
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
    # being run in an isolated environment. For the same reason, pylint is
    # also not able to determine the correct order of imports.
    # One way to fix this is to install all develop dependencies in this nox
    # session, which we do not do. The whole point of static linting tools is
    # to not rely on any package be importable at runtime. Instead, these
    # imports are validated implicitly when the test suite is run.
    session.run('pylint', '--version')
    session.run(
        'pylint', '--disable=import-error', '--disable=wrong-import-order', *locations,
    )


@nox.session(python=[MAIN_PYTHON, NEXT_PYTHON])
def test(session: Session) -> None:
    """Test the code base.

    Runs the unit and integration tests (written with pytest).

    If no extra arguments are provided, the entire test suite
    is exexcuted and succeeds only with 100% coverage.

    If extra arguments are provided, they are
    forwarded to pytest without any changes.
    """
    # Re-using an old environment is not so easy here as
    # `poetry install --no-dev` removes previously installed packages.
    # We keep things simple and forbid such usage.
    if session.virtualenv.reuse_existing:
        raise RuntimeError(
            'The "test" and "pre-merge" sessions must be run without the "-r" option',
        )

    _begin(session)
    # Install only the non-develop dependencies and the testing tool chain.
    session.run('poetry', 'install', '--no-dev', external=True)
    _install_packages(session, 'pytest', 'pytest-cov')
    # Interpret extra arguments as options for pytest.
    # They are "dropped" by the hack in the pre_merge() function
    # if this function is run within the "pre-merge" session.
    posargs = () if session.env.get('_drop_posargs') else session.posargs
    args = posargs or (
        '--cov',
        '--no-cov-on-fail',
        '--cov-branch',
        '--cov-fail-under=100',
        '--cov-report=term-missing:skip-covered',
        PYTEST_LOCATION,
    )
    session.run('pytest', *args)


@nox.session(name='pre-commit', python=MAIN_PYTHON, venv_backend='none')
def pre_commit(session: Session) -> None:
    """Source files must be well-formed before they enter git.

    Intended to be run as a pre-commit hook.

    This session is a wrapper that triggers the "format" and "lint" sessions.

    Passed in extra arguments are forwarded. So, if it is run as a pre-commit
    hook, only the currently staged source files are formatted and linted.
    """
    # "format" and "lint" are run in sessions on their own as
    # session.notify() creates new Session objects.
    session.notify('format')
    session.notify('lint')


@nox.session(name='pre-merge', python=MAIN_PYTHON)
def pre_merge(session: Session) -> None:
    """The test suite must pass before merges are made.

    Intended to be run either as a pre-merge or pre-push hook.

    First, this session triggers the "format" and "lint" sessions via
    the "pre-commit" session.

    Then, it runs the "test" session ignoring any extra arguments passed in
    so that the entire test suite is executed.
    """
    session.notify('pre-commit')
    # Little hack to not work with the extra arguments provided
    # by the pre-commit framework. Create a flag in the
    # env(ironment) that must contain only `str`-like objects.
    session.env['_drop_posargs'] = 'true'
    # Cannot use session.notify() to trigger the "test" session
    # as that would create a new Session object without the flag
    # in the env(ironment). Instead, run the test() function within
    # the "pre-merge" session.
    test(session)


def _begin(session: Session) -> None:
    """Show generic info about a session."""
    if session.posargs:
        # Part of the hack in pre_merge() to "drop" the extra arguments.
        # Indicate to stdout that the passed in extra arguments are ignored.
        if session.env.get('_drop_posargs') is None:
            print('Provided extra argument(s):', *session.posargs)  # noqa:WPS421
        else:
            print('The provided extra arguments are ignored')  # noqa:WPS421

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

    IMPORTANT: This function skips installation if the current nox session
    is run with the "-r" flag to re-use an existing virtual environment.
    That turns nox into a fast task runner provided that a virtual
    environment actually existed and does not need to be changed (e.g.,
    new dependencies added in the meantime). Do not use the "-r" flag on CI
    or as part of pre-commit hooks!

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
