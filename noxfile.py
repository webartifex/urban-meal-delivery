"""Configure nox as the task runner, including CI and pre-commit hooks.

Generic maintainance tasks:

- "init-project": set up the pre-commit hooks

- "clean-pwd": ~ `git clean -X` with minor exceptions


For local development, use the "format", "lint", and "test" sessions
as unified tasks to assure the quality of the source code:

- "format" (autoflake, black, isort):

  + check all source files [default]
  + accept extra arguments, e.g., `poetry run nox -s format -- noxfile.py`,
    that are then interpreted as the paths the formatters and linters work
    on recursively

- "lint" (flake8, mypy): same as "format"

- "test" (pytest, xdoctest):

  + run the entire test suite [default]
  + accepts extra arguments, e.g., `poetry run nox -s test -- --no-cov`,
    that are passed on to `pytest` and `xdoctest` with no changes
    => may be paths or options
"""

import collections
import itertools
import os
import pathlib
import tempfile
from collections.abc import Mapping
from typing import Any, Generator

import nox
from nox.sessions import Session
from packaging import version as pkg_version


def nested_defaultdict() -> collections.defaultdict[str, Any]:
    """Create a multi-level `defaultdict` with variable depth.

    The returned `dict`ionary never raises a `KeyError`
    but always returns an empty `dict`ionary instead.
    This behavior occurs recursively.

    Adjusted from: https://stackoverflow.com/a/8702435
    """
    return collections.defaultdict(nested_defaultdict)


def defaultify(obj: Any) -> Any:
    """Turn nested `dict`s into nested `defaultdict`s."""
    if isinstance(obj, Mapping):
        return collections.defaultdict(
            nested_defaultdict,
            {key: defaultify(val) for key, val in obj.items()},
        )
    return obj


def load_pyproject_toml() -> collections.defaultdict[str, Any]:
    """Load the contents of the pyproject.toml file.

    The contents are represented as a `nested_defaultdict`;
    so, missing keys and tables (i.e., "sections" in the .ini format)
    do not result in `KeyError`s but return empty `nested_defaultdict`s.
    """
    return defaultify(nox.project.load_toml('pyproject.toml'))


def load_supported_python_versions(*, reverse: bool = False) -> list[str]:
    """Parse the Python versions from the pyproject.toml file."""
    pyproject = load_pyproject_toml()
    version_names = {
        classifier.rsplit(' ')[-1]
        for classifier in pyproject['project']['classifiers']
        if classifier.startswith('Programming Language :: Python :: ')
    }
    return sorted(version_names, key=pkg_version.Version, reverse=reverse)


PACKAGE_IMPORT_NAME = 'velofy'

# Docs/sphinx locations.
DOCS_SRC = 'docs/'
DOCS_BUILD = '.cache/docs/'

# Path to the *.py files to be packaged.
PACKAGE_SOURCE_LOCATION = 'src/'

# Path to the test suite.
PYTEST_LOCATION = 'tests/'

# Paths with all *.py files.
SRC_LOCATIONS = (
    f'{DOCS_SRC}conf.py',
    'migrations/env.py',
    'migrations/versions/',
    'noxfile.py',
    'scripts/',
    PACKAGE_SOURCE_LOCATION,
    PYTEST_LOCATION,
)

SUPPORTED_PYTHONS = load_supported_python_versions()

# Must be listed in the "classifiers", which is checked at the bottom
# of this file, and satisfy `requires-python` in pyproject.toml
MAIN_PYTHON = '3.13'

nox.options.default_venv_backend = 'uv'

# Use a unified .cache/ folder for all tools.
nox.options.envdir = '.cache/nox'

# All tools except `git` and `uv` are project dependencies
# => Avoid accidental successes if the environment is not set up properly
nox.options.error_on_external_run = True

# Always start with fresh virtual environments
# unless the "-r" or "-R" flags are passed in
nox.options.reuse_venv = 'no'

# Do not run further sessions once one fails
nox.options.stop_on_first_error = True

# Run only local checks by default.
nox.options.sessions = (
    'format',
    'lint',
    'test',
)

# Make `uv` use its own Python no matter what
# because only then are the headers needed to build `rpy2` from source included
os.environ.setdefault('UV_PYTHON_PREFERENCE', 'only-managed')

# Where to keep temporary files (e.g., the constraints file in `install_pinned()`)
tempfile.tempdir = '.cache/tmp'
os.makedirs(tempfile.tempdir, exist_ok=True)


@nox.session(name='format', python=MAIN_PYTHON)
def format_code(session: Session) -> None:
    """Format source files with autoflake, black, and isort.

    If no extra arguments are provided, all source files are formatted.
    Otherwise, they are interpreted as paths the formatters work on recursively.
    """
    start(session)

    # The formatting tools do not require the developed
    # package be installed in the virtual environment.
    install_pinned(session, 'autoflake', 'black', 'isort')

    # Interpret extra arguments as locations of source files.
    locations = session.posargs or SRC_LOCATIONS

    # `autoflake` only changes files because of "in-place = true"
    # in the "[tool.autoflake]" section in pyproject.toml
    session.run('autoflake', '--version')
    session.run('autoflake', *locations)

    session.run('black', '--version')
    session.run('black', *locations)

    session.run('isort', '--version')
    session.run('isort', *locations)


@nox.session(name='lint', python=MAIN_PYTHON)
def lint_code(session: Session) -> None:
    """Lint source files with flake8 and mypy.

    If no extra arguments are provided, all source files are linted.
    Otherwise, they are interpreted as paths the linters work on recursively.
    """
    start(session)

    # The linting tools do not require the developed
    # package be installed in the virtual environment.
    install_pinned(
        session,
        'flake8',
        'flake8-annotations',
        'flake8-black',
        'flake8-pyproject',
        'flake8-pytest-style',
        'isort',
        'mypy',
    )

    # Interpret extra arguments as locations of source files.
    locations = session.posargs or SRC_LOCATIONS

    # `flake8` reads the "[tool.flake8]" section in pyproject.toml
    # only with the `flake8-pyproject` plugin installed
    session.run('flake8', '--version')
    session.run('flake8', *locations)

    session.run('isort', '--version')
    session.run('isort', '--check-only', *locations)

    # For mypy, only lint *.py files to be packaged.
    mypy_locations = [
        path for path in locations if path.startswith(PACKAGE_SOURCE_LOCATION)
    ]
    if mypy_locations:
        session.run('mypy', '--version')
        session.run('mypy', *mypy_locations)
    else:
        session.log('No paths to be checked with mypy')


@nox.session(name='test', python=MAIN_PYTHON)
def test_code(session: Session) -> None:
    """Test the code base.

    Runs the unit and integration tests with pytest and
    validate that all code snippets in docstrings work with xdoctest.

    If no extra arguments are provided, the entire test suite
    is exexcuted and succeeds only with 100% coverage.

    If extra arguments are provided, they are
    forwarded to pytest and xdoctest without any changes.
    xdoctest ignores arguments it does not understand.
    """

    start(session)

    # The testing tools require the developed package and its
    # non-develop dependencies be installed in the virtual environment.
    # As the package is not installed in editable mode, the coverage report
    # relies on "[tool.coverage.paths]" in pyproject.toml to map to src/.
    install_pinned(
        session,
        '.',
        'Faker',
        'factory-boy',
        'packaging',
        'pytest',
        'pytest-cov',
        'pytest-env',
        'pytest-mock',
        'xdoctest[optional]',
    )

    session.run('pytest', '--version')

    # Both R and a database are available locally and on the CI server.
    # Therefore, we require 100% coverage.
    pytest_args = (
        '--cov',
        '--no-cov-on-fail',
        '--cov-branch',
        '--cov-fail-under=100',
        '--cov-report=term-missing:skip-covered',
        PYTEST_LOCATION,
    )

    # Interpret extra arguments as options for pytest.
    posargs = session.posargs

    session.run('pytest', *(posargs or pytest_args))

    # For xdoctest, the default arguments are different from pytest.
    args = posargs or [PACKAGE_IMPORT_NAME]

    # The "TESTING" environment variable forces the global `engine`, `connection`,
    # and `session` objects to be set to `None` and avoid any database connection.
    # For `pytest` above, `pytest-env` sets it with the "env" option
    # in the "[tool.pytest.ini_options]" section in pyproject.toml.
    session.env['TESTING'] = 'true'

    session.run('xdoctest', '--version')
    session.run('xdoctest', '--quiet', *args)  # --quiet => less verbose output


@nox.session(name='deps-audit', python=MAIN_PYTHON, reuse_venv=False)
def audit_pinned_dependencies(session: Session) -> None:
    """Check dependencies for vulnerabilities with `pip-audit`.

    The dependencies are all those pinned in the uv.lock file.

    `pip-audit` uses the Python Packaging Advisory Database,
    see https://github.com/pypa/advisory-database for details.
    """
    do_not_accept_arguments(session)
    do_not_reuse(session)  # Explicit guard in case `reuse_venv=False` above is removed

    start(session)

    # `pip-audit` is not pinned to always check with its latest version
    session.install('pip-audit')

    with tempfile.NamedTemporaryFile(suffix='.txt') as requirements_txt:
        session.run(
            'uv',
            'export',
            '--all-extras',
            '--all-groups',
            '--locked',
            '--no-emit-project',
            '--quiet',
            f'--output-file={requirements_txt.name}',
        )

        session.run('pip-audit', '--version')
        session.run(
            'pip-audit',
            '--cache-dir=.cache/pip-audit',
            '--disable-pip',
            '--progress-spinner=off',
            f'--requirement={requirements_txt.name}',
            '--strict',
            # TODO: Remove these ignores once we upgrade to `black` v26
            '--ignore-vuln=PYSEC-2026-2120',
            '--ignore-vuln=PYSEC-2026-2121',
            '--ignore-vuln=CVE-2026-114134',
        )


@nox.session(name='docs', python=MAIN_PYTHON)
def build_docs(session: Session) -> None:
    """Build the documentation with sphinx."""

    start(session)

    # The documentation tools require the developed package and its
    # non-develop dependencies be installed in the virtual environment.
    # Otherwise, sphinx's autodoc could not include the docstrings.
    install_pinned(session, '.', 'sphinx', 'sphinx-autodoc-typehints')

    # The "TESTING" environment variable forces the global `engine`, `connection`,
    # and `session` objects to be set to `None` and avoid any database connection.
    session.env['TESTING'] = 'true'

    session.run('sphinx-build', DOCS_SRC, DOCS_BUILD)
    # Verify all external links return 200 OK.
    session.run('sphinx-build', '-b', 'linkcheck', DOCS_SRC, DOCS_BUILD)

    print(f'Docs are available at {os.getcwd()}/{DOCS_BUILD}index.html')  # noqa:WPS421


@nox.session(name='deps-lock', python=MAIN_PYTHON, venv_backend='none')
def lock_dependencies(session: Session) -> None:
    """Lock dependencies in pyproject.toml into uv.lock.

    Convenience task to run after manual changes of dependencies
    in the pyproject.toml file.

    Use `git diff uv.lock` to review the newly pinned versions.
    """
    do_not_accept_arguments(session)

    # Little hack: Create a flag in the env(ironment)
    # and call `upgrade_dependencies()` directly
    # because `session.notify()` starts sessions with a new
    # `nox.Session` object that does not have the flag set
    session.env['_lock_only'] = 'true'

    upgrade_dependencies(session)


@nox.session(name='deps-upgrade', python=MAIN_PYTHON, venv_backend='none')
def upgrade_dependencies(session: Session) -> None:
    """Pin dependencies in uv.lock to their latest MINOR/PATCH versions.

    The allowed versions are the ranges in the pyproject.toml file.

    If no arguments are provided, i.e., `nox -s deps-upgrade`,
    all packages are upgraded!

    If package names are provided as positional arguments,
    e.g., `nox -s deps-upgrade -- pandas`, only those are upgraded.

    The upgrades are not yet synced into the local develop environment!
    Use `nox -s venv` for that.

    Use `git diff uv.lock` to review them.

    So, the obtained upgrades must still be manually
    `git commit`ed into the repository.
    """
    if session.env.get('_lock_only'):
        upgrade = []
    elif session.posargs:
        upgrade = [f'--upgrade-package={pkg_name}' for pkg_name in session.posargs]
    else:
        upgrade = ['--upgrade']

    session.run('uv', '--version', external=True)
    session.run('uv', 'lock', *upgrade, external=True)

    session.run('git', 'diff', '--stat', 'uv.lock', external=True)


@nox.session(name='deps-upgrade-check', python=MAIN_PYTHON)
def check_dependency_upgrades(session: Session) -> None:
    """Check the dependencies in uv.lock for upgrades.

    This task checks if upgrades are available for the PyPI
    packages pinned in the uv.lock file. Also, it obtains
    information about the age of the pinned releases.

    The output is written to ".cache/dependencies_checked.txt".
    """
    do_not_accept_arguments(session)
    start(session)

    # The script only uses the standard library => Nothing to install
    session.run('python', 'scripts/get_update_info_for_dependencies.py')


@nox.session(name='venv', python=MAIN_PYTHON, venv_backend='none')
def create_develop_environment(session: Session) -> None:
    """Set up the local develop environment in ".venv".

    All dependency groups and extras are installed
    with the versions pinned in the uv.lock file.

    If one extra argument is provided, e.g., `uv run nox -s venv -- other-venv`,
    it is used as the location of the environment instead of ".venv".

    Then, `uv run` only uses that environment
    with "UV_PROJECT_ENVIRONMENT" set to the same location.
    """
    location, *further_args = session.posargs or ('.venv',)

    if further_args:
        session.error('Must provide exactly one location')

    # All dependency groups are installed because of "default-groups = 'all'"
    # in the "[tool.uv]" section in pyproject.toml
    session.run(
        'uv',
        'sync',
        '--all-extras',
        '--locked',
        env={'UV_PROJECT_ENVIRONMENT': location},
        external=True,
    )


def _expand(*patterns: str) -> Generator[pathlib.Path, None, None]:
    """Expand glob patterns into (resolved) paths.

    Args:
        *patterns: patterns to be expanded

    Yields:
        expanded: an expanded path
    """
    for pattern in patterns:
        if not (pattern := pattern.strip()):
            continue

        expanded_paths = pathlib.Path.cwd().glob(pattern)

        for path in expanded_paths:
            yield path.resolve()


@nox.session(name='init-project', python=MAIN_PYTHON, venv_backend='none')
def initialize_project(session: Session) -> None:
    """Install the pre-commit hooks."""
    for type_ in ('pre-commit', 'pre-merge-commit', 'pre-push'):
        session.run('uv', 'run', 'pre-commit', 'install', f'--hook-type={type_}')


@nox.session(name='clean-cwd', python=MAIN_PYTHON, venv_backend='none')
def clean_cwd(session: Session) -> None:
    """Remove (almost) all glob patterns listed in git's ignore file.

    Compared to `git clean -X`, never remove local environment variables
    in the ".env" and ".envrc" files, pyenv's ".python-version" file,
    and the local develop environment in ".venv".

    An existing ".cache/" folder is always deleted first.
    """
    do_not_accept_arguments(session)

    do_not_remove = {
        '.env',
        '.envrc',
        '.python-version',
        '.venv',
    }

    with pathlib.Path('.gitignore').open() as fp:
        ignored_patterns = {
            pattern for pattern in fp if pattern and not pattern.startswith(('#', '!'))
        }

    with pathlib.Path('.gitignore').open() as fp:
        excluded_patterns = {pattern[1:] for pattern in fp if pattern.startswith('!')}

    # Paths are resolved into absolute ones to avoid accidental matches
    excluded_paths = {
        pathlib.Path(path).resolve()
        for path in do_not_remove | set(_expand(*excluded_patterns))
    }

    for path in itertools.chain([pathlib.Path('.cache')], _expand(*ignored_patterns)):
        # The `path` must not be a sub-path of an `excluded_path`
        if {path, *path.parents} & excluded_paths:
            continue

        session.run('rm', '-rf', path)


def do_not_accept_arguments(session: Session, *, raise_error: bool = True) -> None:
    """Do not accept any `session.posargs`."""
    if session.posargs:
        msg = 'be run without any positional arguments behind the "--"'
        if raise_error:
            session.error(f'Must {msg}')
        else:
            session.warn(f'Should {msg}')


def do_not_reuse(session: Session, *, raise_error: bool = True) -> None:
    """Do not reuse a session with the "-r" flag."""
    if session._runner.venv._reused:
        msg = 'be run without the "-r" and "-R" flags'
        if raise_error:
            session.error(f'Must {msg}')
        else:
            session.warn(f'Should {msg}')


def start(session: Session) -> None:
    """Show generic info about a session."""
    if session.posargs:
        session.debug(f'Received extra arguments: {session.posargs}')

    session.debug('Some generic information about the environment')
    session.run('python', '--version')
    session.run('python', '-c', 'import sys; print(sys.executable)')
    session.run('python', '-c', 'import sys; print(sys.path)')
    session.run('python', '-c', 'import os; print(os.getcwd())')
    session.run('python', '-c', 'import os; print(os.environ["PATH"])')

    session.env['BLACK_CACHE_DIR'] = '.cache/black'

    session.run(
        'mkdir',
        '-p',
        *(
            f'.cache/{dir_}'
            for dir_ in (
                'black',
                'coverage',
                'mypy',
                'nox',
                'pytest',
                'tmp',
            )
        ),
        external=True,
        log=False,
    )


def install_pinned(
    session: Session,
    *packages_or_pip_args: str,
    **kwargs: Any,
) -> None:
    """Install packages respecting the uv.lock file.

    Wraps `nox.Session.install()` such that it installs packages
    respecting the versions pinned in the uv.lock file,
    exported into a temporary constraints file.
    This makes nox sessions more deterministic.

    The developed package itself (i.e., ".") is only rebuilt
    if a file listed in the "cache-keys" in the "[tool.uv]" section
    in pyproject.toml changes; otherwise, `uv` re-uses a cached build.
    """
    if skip_install(session):
        return

    with tempfile.NamedTemporaryFile(suffix='.txt') as constraints_txt:
        session.run(
            'uv',
            'export',
            '--all-extras',
            '--all-groups',
            '--locked',
            '--no-emit-project',
            '--no-hashes',
            '--quiet',
            f'--output-file={constraints_txt.name}',
        )
        session.install(
            f'--constraint={constraints_txt.name}',
            *packages_or_pip_args,
            **kwargs,
        )


def skip_install(session: Session) -> bool:
    """Installations may be skipped if a virtual environment can be reused.

    Skipping package installations must be requested with the "-R" flag.
    """
    # Same logic to skip package installation as in core `nox`
    # See: https://github.com/wntrblm/nox/blob/2024.10.09/nox/sessions.py#L816
    venv = session._runner.venv
    if session._runner.global_config.no_install and venv._reused:
        return True
    return False


if MAIN_PYTHON not in SUPPORTED_PYTHONS:
    msg = f'MAIN_PYTHON version, v{MAIN_PYTHON}, is not in SUPPORTED_PYTHONS'
    raise RuntimeError(msg)
