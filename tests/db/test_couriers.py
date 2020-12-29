"""Test the ORM's `Courier` model."""
# pylint:disable=no-self-use

import pytest
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `Courier`."""

    def test_create_courier(self, courier):
        """Test instantiation of a new `Courier` object."""
        assert courier is not None

    def test_text_representation(self, courier):
        """`Courier` has a non-literal text representation."""
        result = repr(courier)

        assert result == f'<Courier(#{courier.id})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Courier`."""

    def test_insert_into_database(self, db_session, courier):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Courier).count() == 0

        db_session.add(courier)
        db_session.commit()

        assert db_session.query(db.Courier).count() == 1

    def test_invalid_vehicle(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.vehicle = 'invalid'
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='available_vehicle_types'):
            db_session.commit()

    def test_negative_speed(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.historic_speed = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_speed'):
            db_session.commit()

    def test_unrealistic_speed(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.historic_speed = 999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_speed'):
            db_session.commit()

    def test_negative_capacity(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.capacity = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='capacity_under_200_liters'):
            db_session.commit()

    def test_too_much_capacity(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.capacity = 999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='capacity_under_200_liters'):
            db_session.commit()

    def test_negative_pay_per_hour(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.pay_per_hour = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_pay_per_hour'):
            db_session.commit()

    def test_too_much_pay_per_hour(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.pay_per_hour = 9999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_pay_per_hour'):
            db_session.commit()

    def test_negative_pay_per_order(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.pay_per_order = -1
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_pay_per_order'):
            db_session.commit()

    def test_too_much_pay_per_order(self, db_session, courier):
        """Insert an instance with invalid data."""
        courier.pay_per_order = 999
        db_session.add(courier)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_pay_per_order'):
            db_session.commit()
