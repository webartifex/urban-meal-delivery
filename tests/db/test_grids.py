"""Test the ORM's `Grid` model."""
# pylint:disable=no-self-use

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `Grid`."""

    def test_create_grid(self, grid):
        """Test instantiation of a new `Grid` object."""
        assert grid is not None

    def test_text_representation(self, grid):
        """`Grid` has a non-literal text representation."""
        result = repr(grid)

        assert result == f'<Grid: {grid.pixel_area}>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Grid`."""

    def test_insert_into_database(self, db_session, grid):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Grid).count() == 0

        db_session.add(grid)
        db_session.commit()

        assert db_session.query(db.Grid).count() == 1

    def test_delete_a_referenced_city(self, db_session, grid):
        """Remove a record that is referenced with a FK."""
        db_session.add(grid)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.City).where(db.City.id == grid.city.id)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_grids_to_cities_via_city_id',
        ):
            db_session.execute(stmt)


class TestProperties:
    """Test properties in `Grid`."""

    def test_pixel_area(self, grid):
        """Test `Grid.pixel_area` property."""
        result = grid.pixel_area

        assert result == 1.0
