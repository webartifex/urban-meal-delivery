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

- "lint" (flake8, mypy, pylint): same as "format"

- "test" (pytest, xdoctest):

  + run the entire test suite [default]
  + accepts extra arguments, e.g., `poetry run nox -s test -- --no-cov`,
    that are passed on to `pytest` and `xdoctest` with no changes
    => may be paths or options


GitHub Actions implements a CI workflow:

- "format", "lint", and "test" as above

- "safety": check if dependencies contain known security vulnerabilites

- "docs": build the documentation with sphinx


The pre-commit framework invokes the "pre-commit" and "pre-merge" sessions:

- "pre-commit" before all commits:

  + triggers "format" and "lint" on staged source files
  + => test coverage may be < 100%

- "pre-merge" before all merges and pushes:

  + same as "pre-commit"
  + plus: triggers "test", "safety", and "docs" (that ignore extra arguments)
  + => test coverage is enforced to be 100%

"""

import contextlib
import glob
import os
import re
import shutil
import subprocess  # noqa:S404
import tempfile
from typing import Generator, IO, Tuple

import nox
from nox.sessions import Session


GITHUB_REPOSITORY = 'webartifex/urban-meal-delivery'
PACKAGE_IMPORT_NAME = 'urban_meal_delivery'

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

PYTHON = '3.8'

# Use a unified .cache/ folder for all tools.
nox.options.envdir = '.cache/nox'

# All tools except git and poetry are project dependencies.
# Avoid accidental successes if the environment is not set up properly.
nox.options.error_on_external_run = True

# Run only CI related checks by default.
nox.options.sessions = (
    'format',
    'lint',
    'test',
    'safety',
    'docs',
)


@nox.session(name='format', python=PYTHON)
def format_(session):
    """Format source files with autoflake, black, and isort.

    If no extra arguments are provided, all source files are formatted.
    Otherwise, they are interpreted as paths the formatters work on recursively.
    """
    _begin(session)

    # The formatting tools do not require the developed
    # package be installed in the virtual environment.
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


@nox.session(python=PYTHON)
def lint(session):
    """Lint source files with flake8, mypy, and pylint.

    If no extra arguments are provided, all source files are linted.
    Otherwise, they are interpreted as paths the linters work on recursively.
    """
    _begin(session)

    # The linting tools do not require the developed
    # package be installed in the virtual environment.
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

    # For mypy, only lint *.py files to be packaged.
    mypy_locations = [
        path for path in locations if path.startswith(PACKAGE_SOURCE_LOCATION)
    ]
    if mypy_locations:
        session.run('mypy', '--version')
        session.run('mypy', *mypy_locations)
    else:
        session.log('No paths to be checked with mypy')

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


@nox.session(name='pre-commit', python=PYTHON, venv_backend='none')
def pre_commit(session):
    """Run the format and lint sessions.

    Source files must be well-formed before they enter git.

    Intended to be run as a pre-commit hook.

    Passed in extra arguments are forwarded. So, if it is run as a pre-commit
    hook, only the currently staged source files are formatted and linted.
    """
    # "format" and "lint" are run in sessions on their own as
    # session.notify() creates new Session objects.
    session.notify('format')
    session.notify('lint')


@nox.session(python=PYTHON)
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
    # Re-using an old environment is not so easy here as
    # `poetry install --no-dev` removes previously installed packages.
    # We keep things simple and forbid such usage.
    if session.virtualenv.reuse_existing:
        raise RuntimeError('The "test" session must be run without the "-r" option')

    _begin(session)

    # The testing tools require the developed package and its
    # non-develop dependencies be installed in the virtual environment.
    session.run('poetry', 'install', '--no-dev', external=True)
    _install_packages(
        session,
        'packaging',
        'pytest',
        'pytest-cov',
        'pytest-env',
        'xdoctest[optional]',
    )

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
        '-k',
        'not e2e',
        PYTEST_LOCATION,
    )
    session.run('pytest', '--version')
    session.run('pytest', *args)

    # For xdoctest, the default arguments are different from pytest.
    args = posargs or [PACKAGE_IMPORT_NAME]
    session.run('xdoctest', '--version')
    session.run('xdoctest', '--quiet', *args)  # --quiet => less verbose output


@nox.session(python=PYTHON)
def safety(session):
    """Check the dependencies for known security vulnerabilities."""
    _begin(session)

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
            'safety', 'check', f'--file={requirements_txt.name}', '--full-report',
        )


@nox.session(python=PYTHON)
def docs(session):
    """Build the documentation with sphinx."""
    # The latest version of the package needs to be installed
    # so that sphinx's autodoc can include the latest docstrings.
    if session.virtualenv.reuse_existing:
        raise RuntimeError('The "docs" session must be run without the "-r" option')

    _begin(session)

    # The documentation tools require the developed package and its
    # non-develop dependencies be installed in the virtual environment.
    # Otherwise, sphinx's autodoc could not include the docstrings.
    session.run('poetry', 'install', '--no-dev', external=True)
    _install_packages(session, 'sphinx', 'sphinx-autodoc-typehints')

    session.run('sphinx-build', DOCS_SRC, DOCS_BUILD)
    # Verify all external links return 200 OK.
    session.run('sphinx-build', '-b', 'linkcheck', DOCS_SRC, DOCS_BUILD)

    print(f'Docs are available at {os.getcwd()}/{DOCS_BUILD}index.html')  # noqa:WPS421


@nox.session(name='pre-merge', python=PYTHON)
def pre_merge(session):
    """Run the format, lint, test, safety, and docs sessions.

    Intended to be run either as a pre-merge or pre-push hook.

    Ignores the paths passed in by the pre-commit framework
    for the test, safety, and docs sessions so that the
    entire test suite is executed.
    """
    # Re-using an old environment is not so easy here as the "test" session
    # runs `poetry install --no-dev`, which removes previously installed packages.
    if session.virtualenv.reuse_existing:
        raise RuntimeError(
            'The "pre-merge" session must be run without the "-r" option',
        )

    session.notify('format')
    session.notify('lint')
    session.notify('safety')
    session.notify('docs')

    # Little hack to not work with the extra arguments provided
    # by the pre-commit framework. Create a flag in the
    # env(ironment) that must contain only `str`-like objects.
    session.env['_drop_posargs'] = 'true'

    # Cannot use session.notify() to trigger the "test" session
    # as that would create a new Session object without the flag
    # in the env(ironment). Instead, run the test() function within
    # the "pre-merge" session.
    test(session)


@nox.session(name='fix-branch-references', python=PYTHON, venv_backend='none')
def fix_branch_references(_):  # noqa:WPS210
    """Replace branch references with the current branch.

    Intended to be run as a pre-commit hook.

    Many files in the project (e.g., README.md) contain links to resources
    on github.com or nbviewer.jupyter.org that contain branch labels.

    This task rewrites these links such that they contain the branch reference
    of the current branch.
    """
    # Adjust this to add/remove glob patterns
    # whose links are re-written.
    paths = ['*.md', '**/*.md', '**/*.ipynb']

    branch = (
        subprocess.check_output(  # noqa:S603
            ('git', 'rev-parse', '--abbrev-ref', 'HEAD'),
        )
        .decode()
        .strip()
    )

    rewrites = [
        {
            'name': 'github',
            'pattern': re.compile(
                fr'((((http)|(https))://github\.com/{GITHUB_REPOSITORY}/((blob)|(tree))/)([\w-]+)/)',  # noqa:E501
            ),
            'replacement': fr'\2{branch}/',
        },
        {
            'name': 'nbviewer',
            'pattern': re.compile(
                fr'((((http)|(https))://nbviewer\.jupyter\.org/github/{GITHUB_REPOSITORY}/((blob)|(tree))/)([\w-]+)/)',  # noqa:E501
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


@nox.session(name='init-project', python=PYTHON, venv_backend='none')
def init_project(session):
    """Install the pre-commit hooks."""
    for type_ in ('pre-commit', 'pre-merge-commit', 'pre-push'):
        session.run('poetry', 'run', 'pre-commit', 'install', f'--hook-type={type_}')


@nox.session(name='clean-pwd', python=PYTHON, venv_backend='none')
def clean_pwd(session):  # noqa:WPS210,WPS231
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


def _begin(session):
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


def _install_packages(session: Session, *packages_or_pip_args: str, **kwargs) -> None:
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
# upgrading to isort ^5.3.0 in pyproject.toml.
@contextlib.contextmanager
def _isort_fix(session):
    """Temporarily upgrade to isort 5.3.0."""
    session.install('isort==5.3.0')
    try:
        yield
    finally:
        session.install('isort==4.3.21')
