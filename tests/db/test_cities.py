"""Test the ORM's `City` model."""
# pylint:disable=no-self-use

import pytest

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `City`."""

    def test_create_city(self, city):
        """Test instantiation of a new `City` object."""
        assert city is not None

    def test_text_representation(self, city):
        """`City` has a non-literal text representation."""
        result = repr(city)

        assert result == f'<City({city.name})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `City`."""

    def test_insert_into_database(self, db_session, city):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.City).count() == 0

        db_session.add(city)
        db_session.commit()

        assert db_session.query(db.City).count() == 1


class TestProperties:
    """Test properties in `City`."""

    def test_location_data(self, city, city_data):
        """Test `City.location` property."""
        result = city.location

        assert isinstance(result, dict)
        assert len(result) == 2
        assert result['latitude'] == pytest.approx(city_data['_center_latitude'])
        assert result['longitude'] == pytest.approx(city_data['_center_longitude'])

    def test_viewport_data_overall(self, city):
        """Test `City.viewport` property."""
        result = city.viewport

        assert isinstance(result, dict)
        assert len(result) == 2

    @pytest.mark.parametrize('corner', ['northeast', 'southwest'])
    def test_viewport_data_corners(self, city, city_data, corner):
        """Test `City.viewport` property."""
        result = city.viewport[corner]

        assert isinstance(result, dict)
        assert len(result) == 2
        assert result['latitude'] == pytest.approx(city_data[f'_{corner}_latitude'])
        assert result['longitude'] == pytest.approx(city_data[f'_{corner}_longitude'])
