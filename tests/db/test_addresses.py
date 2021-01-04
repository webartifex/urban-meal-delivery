"""Test the ORM's `Address` model."""
# pylint:disable=no-self-use,protected-access

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db
from urban_meal_delivery.db import utils


class TestSpecialMethods:
    """Test special methods in `Address`."""

    def test_create_address(self, address):
        """Test instantiation of a new `Address` object."""
        assert address is not None

    def test_text_representation(self, address):
        """`Address` has a non-literal text representation."""
        result = repr(address)

        assert result == f'<Address({address.street} in {address.city_name})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Address`."""

    def test_insert_into_database(self, db_session, address):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Address).count() == 0

        db_session.add(address)
        db_session.commit()

        assert db_session.query(db.Address).count() == 1

    def test_delete_a_referenced_address(self, db_session, address, make_address):
        """Remove a record that is referenced with a FK."""
        db_session.add(address)
        # Fake another_address that has the same `._primary_id` as `address`.
        db_session.add(make_address(_primary_id=address.id))
        db_session.commit()

        db_session.delete(address)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_addresses_to_addresses_via_primary_id',
        ):
            db_session.commit()

    def test_delete_a_referenced_city(self, db_session, address):
        """Remove a record that is referenced with a FK."""
        db_session.add(address)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.City).where(db.City.id == address.city.id)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_addresses_to_cities_via_city_id',
        ):
            db_session.execute(stmt)

    @pytest.mark.parametrize('latitude', [-91, 91])
    def test_invalid_latitude(self, db_session, address, latitude):
        """Insert an instance with invalid data."""
        address.latitude = latitude
        db_session.add(address)

        with pytest.raises(
            sa_exc.IntegrityError, match='latitude_between_90_degrees',
        ):
            db_session.commit()

    @pytest.mark.parametrize('longitude', [-181, 181])
    def test_invalid_longitude(self, db_session, address, longitude):
        """Insert an instance with invalid data."""
        address.longitude = longitude
        db_session.add(address)

        with pytest.raises(
            sa_exc.IntegrityError, match='longitude_between_180_degrees',
        ):
            db_session.commit()

    @pytest.mark.parametrize('zip_code', [-1, 0, 9999, 100000])
    def test_invalid_zip_code(self, db_session, address, zip_code):
        """Insert an instance with invalid data."""
        address.zip_code = zip_code
        db_session.add(address)

        with pytest.raises(sa_exc.IntegrityError, match='valid_zip_code'):
            db_session.commit()

    @pytest.mark.parametrize('floor', [-1, 41])
    def test_invalid_floor(self, db_session, address, floor):
        """Insert an instance with invalid data."""
        address.floor = floor
        db_session.add(address)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_floor'):
            db_session.commit()


class TestProperties:
    """Test properties in `Address`."""

    def test_is_primary(self, address):
        """Test `Address.is_primary` property."""
        assert address.id == address._primary_id  # noqa:WPS437

        result = address.is_primary

        assert result is True

    def test_is_not_primary(self, address):
        """Test `Address.is_primary` property."""
        address._primary_id = 999  # noqa:WPS437

        result = address.is_primary

        assert result is False

    def test_location(self, address):
        """Test `Address.location` property."""
        latitude = float(address.latitude)
        longitude = float(address.longitude)

        result = address.location

        assert isinstance(result, utils.Location)
        assert result.latitude == pytest.approx(latitude)
        assert result.longitude == pytest.approx(longitude)

    def test_location_is_cached(self, address):
        """Test `Address.location` property."""
        result1 = address.location
        result2 = address.location

        assert result1 is result2

    def test_x_is_positive(self, address):
        """Test `Address.x` property."""
        result = address.x

        assert result > 0

    def test_y_is_positive(self, address):
        """Test `Address.y` property."""
        result = address.y

        assert result > 0
