"""Test the package's configuration module."""

import pytest

from urban_meal_delivery import configuration


envs = ['production', 'testing']


@pytest.mark.parametrize('env', envs)
def test_config_repr(env):
    """Config objects have the text representation '<configuration>'."""
    config = configuration.make_config(env)

    assert str(config) == '<configuration>'


def test_invalid_config():
    """There are only 'production' and 'testing' configurations."""
    with pytest.raises(ValueError, match="'production' or 'testing'"):
        configuration.make_config('invalid')


@pytest.mark.parametrize('env', envs)
def test_database_uri_set(env, monkeypatch):
    """Package does NOT emit warning if DATABASE_URI is set."""
    uri = 'postgresql://user:password@localhost/db'
    monkeypatch.setattr(configuration.ProductionConfig, 'DATABASE_URI', uri)
    monkeypatch.setattr(configuration.TestingConfig, 'DATABASE_URI', uri)

    # Prevent that a warning is emitted for a missing R_LIBS_PATH.
    monkeypatch.setattr(configuration.Config, 'R_LIBS_PATH', '.cache/r_libs')

    with pytest.warns(None) as record:
        configuration.make_config(env)

    assert len(record) == 0  # noqa:WPS441,WPS507


@pytest.mark.parametrize('env', envs)
def test_no_database_uri_set_with_testing_env_var(env, monkeypatch):
    """Package does not work without DATABASE_URI set in the environment."""
    monkeypatch.setattr(configuration.ProductionConfig, 'DATABASE_URI', None)
    monkeypatch.setattr(configuration.TestingConfig, 'DATABASE_URI', None)

    monkeypatch.setenv('TESTING', 'true')

    # Prevent that a warning is emitted for a missing R_LIBS_PATH.
    monkeypatch.setattr(configuration.Config, 'R_LIBS_PATH', '.cache/r_libs')

    with pytest.warns(None) as record:
        configuration.make_config(env)

    assert len(record) == 0  # noqa:WPS441,WPS507


@pytest.mark.parametrize('env', envs)
def test_no_database_uri_set_without_testing_env_var(env, monkeypatch):
    """Package does not work without DATABASE_URI set in the environment."""
    monkeypatch.setattr(configuration.ProductionConfig, 'DATABASE_URI', None)
    monkeypatch.setattr(configuration.TestingConfig, 'DATABASE_URI', None)

    monkeypatch.delenv('TESTING', raising=False)

    # Prevent that a warning is emitted for a missing R_LIBS_PATH.
    monkeypatch.setattr(configuration.Config, 'R_LIBS_PATH', '.cache/r_libs')

    with pytest.warns(UserWarning, match='no DATABASE_URI'):
        configuration.make_config(env)


@pytest.mark.parametrize('env', envs)
def test_r_libs_path_set(env, monkeypatch):
    """Package does NOT emit a warning if R_LIBS is set in the environment."""
    monkeypatch.setattr(configuration.Config, 'R_LIBS_PATH', '.cache/r_libs')

    # Prevent that a warning is emitted for a missing DATABASE_URI.
    uri = 'postgresql://user:password@localhost/db'
    monkeypatch.setattr(configuration.ProductionConfig, 'DATABASE_URI', uri)

    with pytest.warns(None) as record:
        configuration.make_config(env)

    assert len(record) == 0  # noqa:WPS441,WPS507


@pytest.mark.parametrize('env', envs)
def test_no_r_libs_path_set_with_testing_env_var(env, monkeypatch):
    """Package emits a warning if no R_LIBS is set in the environment ...

    ... when not testing.
    """
    monkeypatch.setattr(configuration.Config, 'R_LIBS_PATH', None)
    monkeypatch.setenv('TESTING', 'true')

    # Prevent that a warning is emitted for a missing DATABASE_URI.
    uri = 'postgresql://user:password@localhost/db'
    monkeypatch.setattr(configuration.ProductionConfig, 'DATABASE_URI', uri)

    with pytest.warns(None) as record:
        configuration.make_config(env)

    assert len(record) == 0  # noqa:WPS441,WPS507


@pytest.mark.parametrize('env', envs)
def test_no_r_libs_path_set_without_testing_env_var(env, monkeypatch):
    """Package emits a warning if no R_LIBS is set in the environment ...

    ... when not testing.
    """
    monkeypatch.setattr(configuration.Config, 'R_LIBS_PATH', None)
    monkeypatch.delenv('TESTING', raising=False)

    # Prevent that a warning is emitted for a missing DATABASE_URI.
    uri = 'postgresql://user:password@localhost/db'
    monkeypatch.setattr(configuration.ProductionConfig, 'DATABASE_URI', uri)

    with pytest.warns(UserWarning, match='no R_LIBS'):
        configuration.make_config(env)


def test_random_testing_schema():
    """CLEAN_SCHEMA is randomized if not set explicitly."""
    result = configuration.random_schema_name()

    assert isinstance(result, str)
    assert result.startswith('temp_')
    assert len(result) == 15
