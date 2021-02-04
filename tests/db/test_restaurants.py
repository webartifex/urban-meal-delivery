"""Test the ORM's `Restaurant` model."""

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `Restaurant`."""

    def test_create_restaurant(self, restaurant):
        """Test instantiation of a new `Restaurant` object."""
        assert restaurant is not None

    def test_text_representation(self, restaurant):
        """`Restaurant` has a non-literal text representation."""
        result = repr(restaurant)

        assert result == f'<Restaurant({restaurant.name})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Restaurant`."""

    def test_insert_into_database(self, db_session, restaurant):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Restaurant).count() == 0

        db_session.add(restaurant)
        db_session.commit()

        assert db_session.query(db.Restaurant).count() == 1

    def test_delete_a_referenced_address(self, db_session, restaurant):
        """Remove a record that is referenced with a FK."""
        db_session.add(restaurant)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Address).where(db.Address.id == restaurant.address.id)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_restaurants_to_addresses_via_address_id',
        ):
            db_session.execute(stmt)

    def test_negative_prep_duration(self, db_session, restaurant):
        """Insert an instance with invalid data."""
        restaurant.estimated_prep_duration = -1
        db_session.add(restaurant)

        with pytest.raises(
            sa_exc.IntegrityError, match='realistic_estimated_prep_duration',
        ):
            db_session.commit()

    def test_too_high_prep_duration(self, db_session, restaurant):
        """Insert an instance with invalid data."""
        restaurant.estimated_prep_duration = 2500
        db_session.add(restaurant)

        with pytest.raises(
            sa_exc.IntegrityError, match='realistic_estimated_prep_duration',
        ):
            db_session.commit()
