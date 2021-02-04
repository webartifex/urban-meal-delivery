"""Test the ORM's `AddressPixelAssociation` model.

Implementation notes:
    The test suite has 100% coverage without the test cases in this module.
    That is so as the `AddressPixelAssociation` model is imported into the
    `urban_meal_delivery.db` namespace so that the `Address` and `Pixel` models
    can find it upon initialization. Yet, none of the other unit tests run any
    code associated with it. Therefore, we test it here as non-e2e tests and do
    not measure its coverage.
"""

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db


@pytest.fixture
def assoc(address, pixel):
    """An association between `address` and `pixel`."""
    return db.AddressPixelAssociation(address=address, pixel=pixel)


@pytest.mark.no_cover
class TestSpecialMethods:
    """Test special methods in `Pixel`."""

    def test_create_an_address_pixel_association(self, assoc):
        """Test instantiation of a new `AddressPixelAssociation` object."""
        assert assoc is not None


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `AddressPixelAssociation`.

    The foreign keys to `City` and `Grid` are tested via INSERT and not
    DELETE statements as the latter would already fail because of foreign
    keys defined in `Address` and `Pixel`.
    """

    def test_insert_into_database(self, db_session, assoc):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.AddressPixelAssociation).count() == 0

        db_session.add(assoc)
        db_session.commit()

        assert db_session.query(db.AddressPixelAssociation).count() == 1

    def test_delete_a_referenced_address(self, db_session, assoc):
        """Remove a record that is referenced with a FK."""
        db_session.add(assoc)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Address).where(db.Address.id == assoc.address.id)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_pixels_to_addresses_via_address_id_city_id',
        ):
            db_session.execute(stmt)

    def test_reference_an_invalid_city(self, db_session, address, pixel):
        """Insert a record with an invalid foreign key."""
        db_session.add(address)
        db_session.add(pixel)
        db_session.commit()

        # Must insert without ORM as otherwise SQLAlchemy figures out
        # that something is wrong before any query is sent to the database.
        stmt = sqla.insert(db.AddressPixelAssociation).values(
            address_id=address.id,
            city_id=999,
            grid_id=pixel.grid.id,
            pixel_id=pixel.id,
        )

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_pixels_to_addresses_via_address_id_city_id',
        ):
            db_session.execute(stmt)

    def test_reference_an_invalid_grid(self, db_session, address, pixel):
        """Insert a record with an invalid foreign key."""
        db_session.add(address)
        db_session.add(pixel)
        db_session.commit()

        # Must insert without ORM as otherwise SQLAlchemy figures out
        # that something is wrong before any query is sent to the database.
        stmt = sqla.insert(db.AddressPixelAssociation).values(
            address_id=address.id,
            city_id=address.city.id,
            grid_id=999,
            pixel_id=pixel.id,
        )

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_pixels_to_grids_via_grid_id_city_id',
        ):
            db_session.execute(stmt)

    def test_delete_a_referenced_pixel(self, db_session, assoc):
        """Remove a record that is referenced with a FK."""
        db_session.add(assoc)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Pixel).where(db.Pixel.id == assoc.pixel.id)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_pixels_to_pixels_via_pixel_id_grid_id',
        ):
            db_session.execute(stmt)

    def test_put_an_address_on_a_grid_twice(self, db_session, address, assoc, pixel):
        """Insert a record that violates a unique constraint."""
        db_session.add(assoc)
        db_session.commit()

        # Create a neighboring `Pixel` and put the same `address` as in `pixel` in it.
        neighbor = db.Pixel(grid=pixel.grid, n_x=pixel.n_x, n_y=pixel.n_y + 1)
        another_assoc = db.AddressPixelAssociation(address=address, pixel=neighbor)

        db_session.add(another_assoc)

        with pytest.raises(sa_exc.IntegrityError, match='duplicate key value'):
            db_session.commit()
