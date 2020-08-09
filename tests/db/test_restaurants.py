"""Test the ORM's Restaurant model."""

import pytest
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import exc as orm_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in Restaurant."""

    # pylint:disable=no-self-use

    def test_create_restaurant(self, restaurant_data):
        """Test instantiation of a new Restaurant object."""
        result = db.Restaurant(**restaurant_data)

        assert result is not None

    def test_text_representation(self, restaurant_data):
        """Restaurant has a non-literal text representation."""
        restaurant = db.Restaurant(**restaurant_data)
        name = restaurant_data['name']

        result = repr(restaurant)

        assert result == f'<Restaurant({name})>'


@pytest.mark.e2e
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in Restaurant."""

    # pylint:disable=no-self-use

    def test_insert_into_database(self, restaurant, db_session):
        """Insert an instance into the database."""
        db_session.add(restaurant)
        db_session.commit()

    def test_dublicate_primary_key(self, restaurant, restaurant_data, db_session):
        """Can only add a record once."""
        db_session.add(restaurant)
        db_session.commit()

        another_restaurant = db.Restaurant(**restaurant_data)
        db_session.add(another_restaurant)

        with pytest.raises(orm_exc.FlushError):
            db_session.commit()

    def test_delete_a_referenced_address(self, restaurant, address, db_session):
        """Remove a record that is referenced with a FK."""
        db_session.add(restaurant)
        db_session.commit()

        with pytest.raises(sa_exc.IntegrityError):
            db_session.execute(
                db.Address.__table__.delete().where(  # noqa:WPS609
                    db.Address.id == address.id,
                ),
            )

    def test_negative_prep_duration(self, restaurant, db_session):
        """Insert an instance with invalid data."""
        restaurant.estimated_prep_duration = -1
        db_session.add(restaurant)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()

    def test_too_high_prep_duration(self, restaurant, db_session):
        """Insert an instance with invalid data."""
        restaurant.estimated_prep_duration = 2500
        db_session.add(restaurant)

        with pytest.raises(sa_exc.IntegrityError):
            db_session.commit()
