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
import contextlib
import glob
import os
import re
import shutil
import subprocess  # noqa:S404
import tempfile
from collections.abc import Mapping
from typing import Any, Generator, IO, Tuple

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


FORGEJO_REPOSITORY = 'code.webartifex.de/alexander/velofy'
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
def format_(session):
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


@nox.session(python=MAIN_PYTHON)
def lint(session):
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


@nox.session(python=MAIN_PYTHON)
def test(session):
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


@nox.session(python=MAIN_PYTHON)
def safety(session):
    """Check the dependencies for known security vulnerabilities."""
    start(session)

    # We do not pin the version of `safety` to always check with
    # the latest version. The risk this breaks the CI is rather low.
    session.install('safety')

    with tempfile.NamedTemporaryFile() as requirements_txt:
        session.run(
            'poetry',
            'export',
            '--dev',
            '--format=requirements.txt',
            f'--output={requirements_txt.name}',
            external=True,
        )
        session.run(
            'safety',
            'check',
            f'--file={requirements_txt.name}',
            '--full-report',
        )


@nox.session(python=MAIN_PYTHON)
def docs(session):
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


@nox.session(name='fix-branch-references', python=MAIN_PYTHON, venv_backend='none')
def fix_branch_references(session):  # noqa:WPS210
    """Replace branch references with the current branch.

    Intended to be run as a pre-commit hook.

    Many files in the project (e.g., README.md) contain links to resources
    on Forgejo that contain branch labels.

    This task rewrites these links such that they contain branch references
    that make sense given the context:

    - If the branch is only a temporary one that is to be merged into
      the 'main' branch, all references are adjusted to 'main' as well.

    - If the branch is not named after a default branch in the GitFlow
      model, it is interpreted as a feature branch and the references
      are adjusted into 'develop'.

    This task may be called with one positional argument that is interpreted
    as the branch to which all references are changed into.
    The format must be "--branch=BRANCH_NAME".
    """
    # Adjust this to add/remove glob patterns
    # whose links are re-written.
    paths = ['*.md', '**/*.md', '**/*.ipynb']

    # Get the branch git is currently on.
    # This is the branch to which all references are changed into
    # if none of the two exceptions below apply.
    branch = (
        subprocess.check_output(  # noqa:S603
            ('git', 'rev-parse', '--abbrev-ref', 'HEAD'),
        )
        .decode()
        .strip()
    )
    # If the current branch is only a temporary one that is to be merged
    # into 'main', we adjust all branch references to 'main' as well.
    if branch.startswith('release') or branch.startswith('research'):
        branch = 'main'
    # If the current branch appears to be a feature branch, we adjust
    # all branch references to 'develop'.
    elif branch != 'main':
        branch = 'develop'
    # If a "--branch=BRANCH_NAME" argument is passed in
    # as the only positional argument, we use BRANCH_NAME.
    # Note: The --branch is required as session.posargs contains
    # the staged files passed in by pre-commit in most cases.
    if session.posargs and len(session.posargs) == 1:
        match = re.match(
            pattern=r'^--branch=([\w\.-]+)$',
            string=session.posargs[0].strip(),
        )
        if match:
            branch = match.groups()[0]

    rewrites = [
        {
            'name': 'forgejo',
            'pattern': re.compile(
                fr'((https://{FORGEJO_REPOSITORY}/src/branch/)([\w\.-]+)/)',
            ),
            'replacement': fr'\2{branch}/',
        },
    ]

    for expanded in _expand(*paths):
        with _line_by_line_replace(expanded) as (old_file, new_file):
            for line in old_file:
                for rewrite in rewrites:
                    line = re.sub(rewrite['pattern'], rewrite['replacement'], line)
                new_file.write(line)


def _expand(*patterns: str) -> Generator[str, None, None]:
    """Expand glob patterns into paths.

    Args:
        *patterns: the patterns to be expanded

    Yields:
        expanded: a single expanded path
    """  # noqa:RST213
    for pattern in patterns:
        yield from glob.glob(pattern.strip())


@contextlib.contextmanager
def _line_by_line_replace(path: str) -> Generator[Tuple[IO, IO], None, None]:
    """Replace/change the lines in a file one by one.

    This generator function yields two file handles, one to the current file
    (i.e., `old_file`) and one to its replacement (i.e., `new_file`).

    Usage: loop over the lines in `old_file` and write the files to be kept
    to `new_file`. Files not written to `new_file` are removed!

    Args:
        path: the file whose lines are to be replaced

    Yields:
        old_file, new_file: handles to a file and its replacement
    """
    file_handle, new_file_path = tempfile.mkstemp()
    with os.fdopen(file_handle, 'w') as new_file:
        with open(path) as old_file:
            yield old_file, new_file

    shutil.copymode(path, new_file_path)
    os.remove(path)
    shutil.move(new_file_path, path)


@nox.session(name='init-project', python=MAIN_PYTHON, venv_backend='none')
def init_project(session):
    """Install the pre-commit hooks."""
    for type_ in ('pre-commit', 'pre-merge-commit', 'pre-push'):
        session.run('uv', 'run', 'pre-commit', 'install', f'--hook-type={type_}')


@nox.session(name='clean-pwd', python=MAIN_PYTHON, venv_backend='none')
def clean_pwd(session):
    """Remove (almost) all glob patterns listed in .gitignore.

    The difference compared to `git clean -X` is that this task
    does not remove pyenv's .python-version file and poetry's
    virtual environment.
    """
    exclude = frozenset(('.env', '.python-version', '.venv/', 'venv/'))

    with open('.gitignore') as file_handle:
        paths = file_handle.readlines()

    for path in _expand(*paths):
        if path.startswith('#'):
            continue

        for excluded in exclude:
            if path.startswith(excluded):
                break
        else:
            session.run('rm', '-rf', path)


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
