"""Test the ORM's `City` model."""
# pylint:disable=no-self-use

import pytest

from urban_meal_delivery import db
from urban_meal_delivery.db import utils


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

    def test_center(self, city, city_data):
        """Test `City.center` property."""
        result = city.center

        assert isinstance(result, utils.Location)
        assert result.latitude == pytest.approx(city_data['_center_latitude'])
        assert result.longitude == pytest.approx(city_data['_center_longitude'])

    def test_center_is_cached(self, city):
        """Test `City.center` property."""
        result1 = city.center
        result2 = city.center

        assert result1 is result2

    def test_northeast(self, city, city_data):
        """Test `City.northeast` property."""
        result = city.northeast

        assert isinstance(result, utils.Location)
        assert result.latitude == pytest.approx(city_data['_northeast_latitude'])
        assert result.longitude == pytest.approx(city_data['_northeast_longitude'])

    def test_northeast_is_cached(self, city):
        """Test `City.northeast` property."""
        result1 = city.northeast
        result2 = city.northeast

        assert result1 is result2

    def test_southwest(self, city, city_data):
        """Test `City.southwest` property."""
        result = city.southwest

        assert isinstance(result, utils.Location)
        assert result.latitude == pytest.approx(city_data['_southwest_latitude'])
        assert result.longitude == pytest.approx(city_data['_southwest_longitude'])

    def test_southwest_is_cached(self, city):
        """Test `City.southwest` property."""
        result1 = city.southwest
        result2 = city.southwest

        assert result1 is result2

    def test_total_x(self, city):
        """Test `City.total_x` property."""
        result = city.total_x

        assert result > 18_000

    def test_total_y(self, city):
        """Test `City.total_y` property."""
        result = city.total_y

        assert result > 9_000
