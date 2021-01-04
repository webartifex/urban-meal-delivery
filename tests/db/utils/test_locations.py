"""Test the `Location` class."""
# pylint:disable=no-self-use

import pytest

from urban_meal_delivery.db import utils


# All tests take place in Paris.
MIN_EASTING, MAX_EASTING = 443_100, 461_200
MIN_NORTHING, MAX_NORTHING = 5_407_200, 5_416_800
ZONE = '31U'


@pytest.fixture
def location(address):
    """A `Location` object based off the `address` fixture."""
    obj = utils.Location(address.latitude, address.longitude)

    assert obj.zone == ZONE  # sanity check

    return obj


@pytest.fixture
def faraway_location():
    """A `Location` object far away from the `location`."""
    obj = utils.Location(latitude=0, longitude=0)

    assert obj.zone != ZONE  # sanity check

    return obj


@pytest.fixture
def origin(city):
    """A `Location` object based off the one and only `city`."""
    obj = city.as_xy_origin

    assert obj.zone == ZONE  # sanity check

    return obj


class TestSpecialMethods:
    """Test special methods in `Location`."""

    def test_create_utm_coordinates(self, location):
        """Test instantiation of a new `Location` object."""
        assert location is not None

    def test_text_representation(self, location):
        """The text representation is a non-literal."""
        result = repr(location)

        assert result.startswith('<Location:')
        assert result.endswith('>')

    @pytest.mark.e2e
    def test_coordinates_in_the_text_representation(self, location):
        """Test the UTM convention in the non-literal text `repr()`.

        Example Format:
            `<UTM: 17T 630084 4833438>'`
        """
        result = repr(location)

        parts = result.split(' ')
        zone = parts[1]
        easting = int(parts[2])
        northing = int(parts[3][:-1])  # strip the ending ">"

        assert zone == location.zone
        assert MIN_EASTING < easting < MAX_EASTING
        assert MIN_NORTHING < northing < MAX_NORTHING

    def test_compare_utm_coordinates_to_different_data_type(self, location):
        """Test `Location.__eq__()`."""
        result = location == object()

        assert result is False

    def test_compare_utm_coordinates_to_far_away_coordinates(
        self, location, faraway_location,
    ):
        """Test `Location.__eq__()`."""
        with pytest.raises(ValueError, match='must be in the same zone'):
            bool(location == faraway_location)

    def test_compare_utm_coordinates_to_equal_coordinates(self, location, address):
        """Test `Location.__eq__()`."""
        same_location = utils.Location(address.latitude, address.longitude)

        result = location == same_location

        assert result is True

    def test_compare_utm_coordinates_to_themselves(self, location):
        """Test `Location.__eq__()`."""
        # pylint:disable=comparison-with-itself
        result = location == location  # noqa:WPS312

        assert result is True

    def test_compare_utm_coordinates_to_different_coordinates(self, location, origin):
        """Test `Location.__eq__()`."""
        result = location == origin

        assert result is False


class TestProperties:
    """Test properties in `Location`."""

    def test_latitude(self, location, address):
        """Test `Location.latitude` property."""
        result = location.latitude

        assert result == pytest.approx(float(address.latitude))

    def test_longitude(self, location, address):
        """Test `Location.longitude` property."""
        result = location.longitude

        assert result == pytest.approx(float(address.longitude))

    def test_easting(self, location):
        """Test `Location.easting` property."""
        result = location.easting

        assert MIN_EASTING < result < MAX_EASTING

    def test_northing(self, location):
        """Test `Location.northing` property."""
        result = location.northing

        assert MIN_NORTHING < result < MAX_NORTHING

    def test_zone(self, location):
        """Test `Location.zone` property."""
        result = location.zone

        assert result == ZONE


class TestRelateTo:
    """Test the `Location.relate_to()` method and the `.x` and `.y` properties."""

    def test_run_relate_to_twice(self, location, origin):
        """The `.relate_to()` method must only be run once."""
        location.relate_to(origin)

        with pytest.raises(RuntimeError, match='once'):
            location.relate_to(origin)

    def test_call_relate_to_with_wrong_other_type(self, location):
        """`other` must be another `Location`."""
        with pytest.raises(TypeError, match='Location'):
            location.relate_to(object())

    def test_call_relate_to_with_far_away_other(
        self, location, faraway_location,
    ):
        """The `other` origin must be in the same UTM zone."""
        with pytest.raises(ValueError, match='must be in the same zone'):
            location.relate_to(faraway_location)

    def test_access_x_without_origin(self, location):
        """`.relate_to()` must be called before `.x` can be accessed."""
        with pytest.raises(RuntimeError, match='origin to relate to must be set'):
            int(location.x)

    def test_access_y_without_origin(self, location):
        """`.relate_to()` must be called before `.y` can be accessed."""
        with pytest.raises(RuntimeError, match='origin to relate to must be set'):
            int(location.y)

    def test_origin_must_be_lower_left_when_relating_to_oneself(self, location):
        """`.x` and `.y` must be `== (0, 0)` when oneself is the origin."""
        location.relate_to(location)

        assert (location.x, location.y) == (0, 0)

    @pytest.mark.e2e
    def test_x_and_y_must_not_be_lower_left_for_address_in_city(self, location, origin):
        """`.x` and `.y` must be `> (0, 0)` when oneself is the origin."""
        location.relate_to(origin)

        assert location.x > 0
        assert location.y > 0
