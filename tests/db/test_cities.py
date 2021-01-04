"""Test the ORM's `City` model."""
# pylint:disable=no-self-use

import pytest

from tests.db.utils import test_locations as consts
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

    def test_viewport_overall(self, city):
        """Test `City.viewport` property."""
        result = city.viewport

        assert isinstance(result, dict)
        assert len(result) == 2

    @pytest.mark.parametrize('corner', ['northeast', 'southwest'])
    def test_viewport_corners(self, city, city_data, corner):
        """Test `City.viewport` property."""
        result = city.viewport[corner]

        assert isinstance(result, utils.Location)
        assert result.latitude == pytest.approx(city_data[f'_{corner}_latitude'])
        assert result.longitude == pytest.approx(city_data[f'_{corner}_longitude'])

    def test_viewport_is_cached(self, city):
        """Test `City.viewport` property."""
        result1 = city.viewport
        result2 = city.viewport

        assert result1 is result2

    def test_city_as_xy_origin(self, city):
        """Test `City.as_xy_origin` property."""
        result = city.as_xy_origin

        assert result.zone == consts.ZONE
        assert consts.MIN_EASTING < result.easting < consts.MAX_EASTING
        assert consts.MIN_NORTHING < result.northing < consts.MAX_NORTHING
