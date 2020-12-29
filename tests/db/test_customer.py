"""Test the ORM's `Customer` model."""
# pylint:disable=no-self-use

import pytest

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `Customer`."""

    def test_create_customer(self, customer):
        """Test instantiation of a new `Customer` object."""
        assert customer is not None

    def test_text_representation(self, customer):
        """`Customer` has a non-literal text representation."""
        result = repr(customer)

        assert result == f'<Customer(#{customer.id})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Customer`."""

    def test_insert_into_database(self, db_session, customer):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Customer).count() == 0

        db_session.add(customer)
        db_session.commit()

        assert db_session.query(db.Customer).count() == 1
