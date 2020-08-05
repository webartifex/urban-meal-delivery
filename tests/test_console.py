"""Test the package's `umd` command-line client."""

import click
import pytest
from click import testing as click_testing

from urban_meal_delivery import console


class TestShowVersion:
    """Test console.show_version().

    The function is used as a callback to a click command option.

    show_version() prints the name and version of the installed package to
    stdout. The output looks like this: "{pkg_name}, version {version}".

    Development (= non-final) versions are indicated by appending a
    " (development)" to the output.
    """

    # pylint:disable=no-self-use

    @pytest.fixture
    def ctx(self) -> click.Context:
        """Context around the console.main Command."""
        return click.Context(console.main)

    def test_no_version(self, capsys, ctx):
        """The the early exit branch without any output."""
        console.show_version(ctx, _param='discarded', value=False)

        captured = capsys.readouterr()

        assert captured.out == ''

    def test_final_version(self, capsys, ctx, monkeypatch):
        """For final versions, NO "development" warning is emitted."""
        version = '1.2.3'
        monkeypatch.setattr(console.urban_meal_delivery, '__version__', version)

        with pytest.raises(click.exceptions.Exit):
            console.show_version(ctx, _param='discarded', value=True)

        captured = capsys.readouterr()

        assert captured.out.endswith(f', version {version}\n')

    def test_develop_version(self, capsys, ctx, monkeypatch):
        """For develop versions, a warning thereof is emitted."""
        version = '1.2.3.dev0'
        monkeypatch.setattr(console.urban_meal_delivery, '__version__', version)

        with pytest.raises(click.exceptions.Exit):
            console.show_version(ctx, _param='discarded', value=True)

        captured = capsys.readouterr()

        assert captured.out.strip().endswith(f', version {version} (development)')


class TestCLI:
    """Test the `umd` CLI utility.

    The test cases are integration tests.
    Therefore, they are not considered for coverage reporting.
    """

    # pylint:disable=no-self-use

    @pytest.fixture
    def cli(self) -> click_testing.CliRunner:
        """Initialize Click's CLI Test Runner."""
        return click_testing.CliRunner()

    @pytest.mark.no_cover
    def test_no_options(self, cli):
        """Exit with 0 status code and no output if run without options."""
        result = cli.invoke(console.main)

        assert result.exit_code == 0
        assert result.output == ''

    # The following test cases validate the --version / -V option.

    version_options = ('--version', '-V')

    @pytest.mark.no_cover
    @pytest.mark.parametrize('option', version_options)
    def test_final_version(self, cli, monkeypatch, option):
        """For final versions, NO "development" warning is emitted."""
        version = '1.2.3'
        monkeypatch.setattr(console.urban_meal_delivery, '__version__', version)

        result = cli.invoke(console.main, option)

        assert result.exit_code == 0
        assert result.output.strip().endswith(f', version {version}')

    @pytest.mark.no_cover
    @pytest.mark.parametrize('option', version_options)
    def test_develop_version(self, cli, monkeypatch, option):
        """For develop versions, a warning thereof is emitted."""
        version = '1.2.3.dev0'
        monkeypatch.setattr(console.urban_meal_delivery, '__version__', version)

        result = cli.invoke(console.main, option)

        assert result.exit_code == 0
        assert result.output.strip().endswith(f', version {version} (development)')
