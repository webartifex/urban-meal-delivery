"""Test the ORM's Address model."""

import pytest
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in Address."""

    # pylint:disable=no-self-use

    def test_create_address(self, address_data):
        """Test instantiation of a new Address object."""
        result = db.Address(**address_data)

        assert result is not None

    def test_text_representation(self, address_data):
        """Address has a non-literal text representation."""
        address = db.Address(**address_data)
        street = address_data['street']
        city_name = address_data['city_name']

        result = repr(address)

        assert result == f'<Address({street} in {city_name})>'


@pytest.mark.e2e
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in Address."""

    # pylint:disable=no-self-use

    def test_insert_into_database(self, address, db_session):
        """Insert an instance into the database."""
        db_session.add(address)
        db_session.commit()

    def test_dublicate_primary_key(self, address, address_data, city, db_session):
        """Can only add a record once."""
        db_session.add(address)
        db_session.commit()

        another_address = db.Address(**address_data)
        another_address.city = city
        db_session.add(another_address)

        with pytest.raises(orm_exc.FlushError):
            db_session.commit()

    def test_delete_a_referenced_address(self, address, address_data, db_session):
        """Remove a record that is referenced with a FK."""
        db_session.add(address)
        db_session.commit()

        # Fake a second address that belongs to the same primary address.
        address_data['id'] += 1
        another_address = db.Address(**address_data)
        db_session.add(another_address)
        db_session.commit()

        with pytest.raises(sa_exc.IntegrityError):
            db_session.execute(
                db.Address.__table__.delete().where(  # noqa:WPS609
                    db.Address.id == address.id,
                ),
            )

    def test_delete_a_referenced_city(self, address, city, db_session):
        """Remove a record that is referenced with a FK."""
        db_session.add(address)
        db_session.commit()

        with pytest.raises(sa_exc.IntegrityError):
            db_session.execute(
                db.City.__table__.delete().where(db.City.id == city.id),  # noqa:WPS609
            )

    @pytest.mark.parametrize('latitude', [-91, 91])
    def test_invalid_latitude(self, address, db_session, latitude):
        """Insert an instance with invalid data."""
        address.latitude = latitude
        db_session.add(address)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    @pytest.mark.parametrize('longitude', [-181, 181])
    def test_invalid_longitude(self, address, db_session, longitude):
        """Insert an instance with invalid data."""
        address.longitude = longitude
        db_session.add(address)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    @pytest.mark.parametrize('zip_code', [-1, 0, 9999, 100000])
    def test_invalid_zip_code(self, address, db_session, zip_code):
        """Insert an instance with invalid data."""
        address.zip_code = zip_code
        db_session.add(address)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    @pytest.mark.parametrize('floor', [-1, 41])
    def test_invalid_floor(self, address, db_session, floor):
        """Insert an instance with invalid data."""
        address.floor = floor
        db_session.add(address)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()


class TestProperties:
    """Test properties in Address."""

    # pylint:disable=no-self-use

    def test_is_primary(self, address_data):
        """Test Address.is_primary property."""
        address = db.Address(**address_data)

        result = address.is_primary

        assert result is True

    def test_is_not_primary(self, address_data):
        """Test Address.is_primary property."""
        address_data['_primary_id'] = 999
        address = db.Address(**address_data)

        result = address.is_primary

        assert result is False
