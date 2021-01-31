"""Test the ORM's `Pixel` model."""

import pytest
import sqlalchemy as sqla
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db


class TestSpecialMethods:
    """Test special methods in `Pixel`."""

    def test_create_pixel(self, pixel):
        """Test instantiation of a new `Pixel` object."""
        assert pixel is not None

    def test_text_representation(self, pixel):
        """`Pixel` has a non-literal text representation."""
        result = repr(pixel)

        assert result == f'<Pixel: ({pixel.n_x}, {pixel.n_y})>'


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `Pixel`."""

    def test_insert_into_database(self, db_session, pixel):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.Pixel).count() == 0

        db_session.add(pixel)
        db_session.commit()

        assert db_session.query(db.Pixel).count() == 1

    def test_delete_a_referenced_grid(self, db_session, pixel):
        """Remove a record that is referenced with a FK."""
        db_session.add(pixel)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Grid).where(db.Grid.id == pixel.grid.id)

        with pytest.raises(
            sa_exc.IntegrityError, match='fk_pixels_to_grids_via_grid_id',
        ):
            db_session.execute(stmt)

    def test_negative_n_x(self, db_session, pixel):
        """Insert an instance with invalid data."""
        pixel.n_x = -1
        db_session.add(pixel)

        with pytest.raises(sa_exc.IntegrityError, match='n_x_is_positive'):
            db_session.commit()

    def test_negative_n_y(self, db_session, pixel):
        """Insert an instance with invalid data."""
        pixel.n_y = -1
        db_session.add(pixel)

        with pytest.raises(sa_exc.IntegrityError, match='n_y_is_positive'):
            db_session.commit()

    def test_non_unique_coordinates_within_a_grid(self, db_session, pixel):
        """Insert an instance with invalid data."""
        another_pixel = db.Pixel(grid=pixel.grid, n_x=pixel.n_x, n_y=pixel.n_y)
        db_session.add(another_pixel)

        with pytest.raises(sa_exc.IntegrityError, match='duplicate key value'):
            db_session.commit()


class TestProperties:
    """Test properties in `Pixel`."""

    def test_side_length(self, pixel):
        """Test `Pixel.side_length` property."""
        result = pixel.side_length

        assert result == 1_000

    def test_area(self, pixel):
        """Test `Pixel.area` property."""
        result = pixel.area

        assert result == 1.0

    def test_northeast(self, pixel):
        """Test `Pixel.northeast` property."""
        result = pixel.northeast

        assert abs(result.x - pixel.side_length) < 2
        assert abs(result.y - pixel.side_length) < 2

    def test_northeast_is_cached(self, pixel):
        """Test `Pixel.northeast` property."""
        result1 = pixel.northeast
        result2 = pixel.northeast

        assert result1 is result2

    def test_southwest(self, pixel):
        """Test `Pixel.southwest` property."""
        result = pixel.southwest

        assert abs(result.x) < 2
        assert abs(result.y) < 2

    def test_southwest_is_cached(self, pixel):
        """Test `Pixel.southwest` property."""
        result1 = pixel.southwest
        result2 = pixel.southwest

        assert result1 is result2

    @pytest.fixture
    def _restaurants_mock(self, mocker, monkeypatch, restaurant):
        """A `Mock` whose `.return_value` is `[restaurant]`."""
        mock = mocker.Mock()
        query = (  # noqa:ECE001
            mock.query.return_value.join.return_value.filter.return_value.all  # noqa:E501,WPS219
        )
        query.return_value = [restaurant]
        monkeypatch.setattr(db, 'session', mock)

    @pytest.mark.usefixtures('_restaurants_mock')
    def test_restaurants(self, pixel, restaurant):
        """Test `Pixel.restaurants` property."""
        result = pixel.restaurants

        assert result == [restaurant]

    @pytest.mark.usefixtures('_restaurants_mock')
    def test_restaurants_is_cached(self, pixel):
        """Test `Pixel.restaurants` property."""
        result1 = pixel.restaurants
        result2 = pixel.restaurants

        assert result1 is result2

    @pytest.mark.db
    def test_restaurants_with_db(self, pixel):
        """Test `Pixel.restaurants` property.

        This is a trivial integration test.
        """
        result = pixel.restaurants

        assert not result  # = empty `list`
