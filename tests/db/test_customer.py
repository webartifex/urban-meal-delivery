"""Test the ORM's Customer model."""

import pytest
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in Customer."""

    # pylint:disable=no-self-use

    def test_create_customer(self, customer_data):
        """Test instantiation of a new Customer object."""
        result = db.Customer(**customer_data)

        assert result is not None

    def test_text_representation(self, customer_data):
        """Customer has a non-literal text representation."""
        customer = db.Customer(**customer_data)
        id_ = customer_data['id']

        result = repr(customer)

        assert result == f'<Customer(#{id_})>'


@pytest.mark.e2e
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in Customer."""

    # pylint:disable=no-self-use

    def test_insert_into_database(self, customer, db_session):
        """Insert an instance into the database."""
        db_session.add(customer)
        db_session.commit()

    def test_dublicate_primary_key(self, customer, customer_data, db_session):
        """Can only add a record once."""
        db_session.add(customer)
        db_session.commit()

        another_customer = db.Customer(**customer_data)
        db_session.add(another_customer)

        with pytest.raises(orm_exc.FlushError):
            db_session.commit()
