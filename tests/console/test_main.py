"""Test the package's top-level `umd` CLI command."""

import click
import pytest

from urban_meal_delivery.console import main


class TestShowVersion:
    """Test `console.main.show_version()`.

    The function is used as a callback to a click command option.

    `show_version()` prints the name and version of the installed package to
    stdout. The output looks like this: "{pkg_name}, version {version}".

    Development (= non-final) versions are indicated by appending a
    " (development)" to the output.
    """

    # pylint:disable=no-self-use

    @pytest.fixture
    def ctx(self) -> click.Context:
        """Context around the `main.entry_point` Command."""
        return click.Context(main.entry_point)

    def test_no_version(self, capsys, ctx):
        """Test the early exit branch without any output."""
        main.show_version(ctx, _param='discarded', value=False)

        captured = capsys.readouterr()

        assert captured.out == ''

    def test_final_version(self, capsys, ctx, monkeypatch):
        """For final versions, NO "development" warning is emitted."""
        version = '1.2.3'
        monkeypatch.setattr(main.urban_meal_delivery, '__version__', version)

        with pytest.raises(click.exceptions.Exit):
            main.show_version(ctx, _param='discarded', value=True)

        captured = capsys.readouterr()

        assert captured.out.endswith(f', version {version}\n')

    def test_develop_version(self, capsys, ctx, monkeypatch):
        """For develop versions, a warning thereof is emitted."""
        version = '1.2.3.dev0'
        monkeypatch.setattr(main.urban_meal_delivery, '__version__', version)

        with pytest.raises(click.exceptions.Exit):
            main.show_version(ctx, _param='discarded', value=True)

        captured = capsys.readouterr()

        assert captured.out.strip().endswith(f', version {version} (development)')


class TestCLIWithoutCommand:
    """Test the `umd` CLI utility, invoked without any specific command.

    The test cases are integration tests.
    Therefore, they are not considered for coverage reporting.
    """

    # pylint:disable=no-self-use

    @pytest.mark.no_cover
    def test_no_options(self, cli):
        """Exit with 0 status code and no output if run without options."""
        result = cli.invoke(main.entry_point)

        assert result.exit_code == 0

    # The following test cases validate the --version / -V option.

    version_options = ('--version', '-V')

    @pytest.mark.no_cover
    @pytest.mark.parametrize('option', version_options)
    def test_final_version(self, cli, monkeypatch, option):
        """For final versions, NO "development" warning is emitted."""
        version = '1.2.3'
        monkeypatch.setattr(main.urban_meal_delivery, '__version__', version)

        result = cli.invoke(main.entry_point, option)

        assert result.exit_code == 0
        assert result.output.strip().endswith(f', version {version}')

    @pytest.mark.no_cover
    @pytest.mark.parametrize('option', version_options)
    def test_develop_version(self, cli, monkeypatch, option):
        """For develop versions, a warning thereof is emitted."""
        version = '1.2.3.dev0'
        monkeypatch.setattr(main.urban_meal_delivery, '__version__', version)

        result = cli.invoke(main.entry_point, option)

        assert result.exit_code == 0
        assert result.output.strip().endswith(f', version {version} (development)')
