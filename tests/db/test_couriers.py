"""Test the ORM's Courier model."""

import pytest
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in Courier."""

    # pylint:disable=no-self-use

    def test_create_courier(self, courier_data):
        """Test instantiation of a new Courier object."""
        result = db.Courier(**courier_data)

        assert result is not None

    def test_text_representation(self, courier_data):
        """Courier has a non-literal text representation."""
        courier_data['id'] = 1
        courier = db.Courier(**courier_data)
        id_ = courier_data['id']

        result = repr(courier)

        assert result == f'<Courier(#{id_})>'


@pytest.mark.e2e
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in Courier."""

    # pylint:disable=no-self-use

    def test_insert_into_database(self, courier, db_session):
        """Insert an instance into the database."""
        db_session.add(courier)
        db_session.commit()

    def test_dublicate_primary_key(self, courier, courier_data, db_session):
        """Can only add a record once."""
        db_session.add(courier)
        db_session.commit()

        another_courier = db.Courier(**courier_data)
        db_session.add(another_courier)

        with pytest.raises(orm_exc.FlushError):
            db_session.commit()

    def test_invalid_vehicle(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.vehicle = 'invalid'
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_negative_speed(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.historic_speed = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_unrealistic_speed(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.historic_speed = 999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_negative_capacity(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.capacity = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_too_much_capacity(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.capacity = 999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_negative_pay_per_hour(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.pay_per_hour = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_too_much_pay_per_hour(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.pay_per_hour = 9999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_negative_pay_per_order(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.pay_per_order = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_too_much_pay_per_order(self, courier, db_session):
        """Insert an instance with invalid data."""
        courier.pay_per_order = 999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()
