"""Test the ORM's City model."""

import pytest
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in City."""

    # pylint:disable=no-self-use

    def test_create_city(self, city_data):
        """Test instantiation of a new City object."""
        result = db.City(**city_data)

        assert result is not None

    def test_text_representation(self, city_data):
        """City has a non-literal text representation."""
        city = db.City(**city_data)
        name = city_data['name']

        result = repr(city)

        assert result == f'<City({name})>'


@pytest.mark.e2e
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in City."""

    # pylint:disable=no-self-use

    def test_insert_into_database(self, city, db_session):
        """Insert an instance into the database."""
        db_session.add(city)
        db_session.commit()

    def test_dublicate_primary_key(self, city, city_data, db_session):
        """Can only add a record once."""
        db_session.add(city)
        db_session.commit()

        another_city = db.City(**city_data)
        db_session.add(another_city)

        with pytest.raises(orm_exc.FlushError):
            db_session.commit()


class TestProperties:
    """Test properties in City."""

    # pylint:disable=no-self-use

    def test_location_data(self, city_data):
        """Test City.location property."""
        city = db.City(**city_data)

        result = city.location

        assert isinstance(result, dict)
        assert len(result) == 2
        assert result['latitude'] == pytest.approx(city_data['_center_latitude'])
        assert result['longitude'] == pytest.approx(city_data['_center_longitude'])

    def test_viewport_data_overall(self, city_data):
        """Test City.viewport property."""
        city = db.City(**city_data)

        result = city.viewport

        assert isinstance(result, dict)
        assert len(result) == 2

    def test_viewport_data_northeast(self, city_data):
        """Test City.viewport property."""
        city = db.City(**city_data)

        result = city.viewport['northeast']

        assert isinstance(result, dict)
        assert len(result) == 2
        assert result['latitude'] == pytest.approx(city_data['_northeast_latitude'])
        assert result['longitude'] == pytest.approx(city_data['_northeast_longitude'])

    def test_viewport_data_southwest(self, city_data):
        """Test City.viewport property."""
        city = db.City(**city_data)

        result = city.viewport['southwest']

        assert isinstance(result, dict)
        assert len(result) == 2
        assert result['latitude'] == pytest.approx(city_data['_southwest_latitude'])
        assert result['longitude'] == pytest.approx(city_data['_southwest_longitude'])
