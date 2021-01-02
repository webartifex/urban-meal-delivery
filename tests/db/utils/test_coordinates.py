"""Test the `UTMCoordinate` class."""
# pylint:disable=no-self-use

import pytest

from urban_meal_delivery.db import utils


# All tests take place in Paris.
MIN_EASTING, MAX_EASTING = 443_100, 461_200
MIN_NORTHING, MAX_NORTHING = 5_407_200, 5_416_800
ZONE = '31U'


@pytest.fixture
def location(address):
    """A `UTMCoordinate` object based off the `address` fixture."""
    obj = utils.UTMCoordinate(address.latitude, address.longitude)

    assert obj.zone == ZONE  # sanity check

    return obj


@pytest.fixture
def faraway_location():
    """A `UTMCoordinate` object far away from the `location`."""
    obj = utils.UTMCoordinate(latitude=0, longitude=0)

    assert obj.zone != ZONE  # sanity check

    return obj


@pytest.fixture
def origin(city):
    """A `UTMCoordinate` object based off the one and only `city`."""
    # Use the `city`'s lower left viewport corner as the `(0, 0)` origin.
    lower_left = city.viewport['southwest']
    obj = utils.UTMCoordinate(lower_left['latitude'], lower_left['longitude'])

    assert obj.zone == ZONE  # sanity check

    return obj


class TestSpecialMethods:
    """Test special methods in `UTMCoordinate`."""

    def test_create_utm_coordinates(self, location):
        """Test instantiation of a new `UTMCoordinate` object."""
        assert location is not None

    def test_create_utm_coordinates_with_origin(self, address, origin):
        """Test instantiation with a `relate_to` argument."""
        result = utils.UTMCoordinate(
            latitude=address.latitude, longitude=address.longitude, relative_to=origin,
        )

        assert result is not None

    def test_create_utm_coordinates_with_non_utm_origin(self):
        """Test instantiation with a `relate_to` argument of the wrong type."""
        with pytest.raises(TypeError, match='UTMCoordinate'):
            utils.UTMCoordinate(
                latitude=0, longitude=0, relative_to=object(),
            )

    def test_create_utm_coordinates_with_invalid_origin(
        self, address, faraway_location,
    ):
        """Test instantiation with a `relate_to` argument at an invalid location."""
        with pytest.raises(ValueError, match='must be in the same UTM zone'):
            utils.UTMCoordinate(
                latitude=address.latitude,
                longitude=address.longitude,
                relative_to=faraway_location,
            )

    def test_text_representation(self, location):
        """The text representation is a non-literal."""
        result = repr(location)

        assert result.startswith('<UTM:')
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
        """Test `UTMCoordinate.__eq__()`."""
        result = location == object()

        assert result is False

    def test_compare_utm_coordinates_to_far_away_coordinates(
        self, location, faraway_location,
    ):
        """Test `UTMCoordinate.__eq__()`."""
        with pytest.raises(ValueError, match='must be in the same zone'):
            bool(location == faraway_location)

    def test_compare_utm_coordinates_to_equal_coordinates(self, location, address):
        """Test `UTMCoordinate.__eq__()`."""
        same_location = utils.UTMCoordinate(address.latitude, address.longitude)

        result = location == same_location

        assert result is True

    def test_compare_utm_coordinates_to_themselves(self, location):
        """Test `UTMCoordinate.__eq__()`."""
        # pylint:disable=comparison-with-itself
        result = location == location  # noqa:WPS312

        assert result is True

    def test_compare_utm_coordinates_to_different_coordinates(self, location, origin):
        """Test `UTMCoordinate.__eq__()`."""
        result = location == origin

        assert result is False


class TestProperties:
    """Test properties in `UTMCoordinate`."""

    def test_easting(self, location):
        """Test `UTMCoordinate.easting` property."""
        result = location.easting

        assert MIN_EASTING < result < MAX_EASTING

    def test_northing(self, location):
        """Test `UTMCoordinate.northing` property."""
        result = location.northing

        assert MIN_NORTHING < result < MAX_NORTHING

    def test_zone(self, location):
        """Test `UTMCoordinate.zone` property."""
        result = location.zone

        assert result == ZONE


class TestRelateTo:
    """Test the `UTMCoordinate.relate_to()` method and the `.x` and `.y` properties."""

    def test_run_relate_to_twice(self, location, origin):
        """The `.relate_to()` method must only be run once."""
        location.relate_to(origin)

        with pytest.raises(RuntimeError, match='once'):
            location.relate_to(origin)

    def test_call_relate_to_with_wrong_other_type(self, location):
        """`other` must be another `UTMCoordinate`."""
        with pytest.raises(TypeError, match='UTMCoordinate'):
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
