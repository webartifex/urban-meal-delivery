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

    def test_two_grids_with_identical_side_length(self, db_session, grid):
        """Insert a record that violates a unique constraint."""
        db_session.add(grid)
        db_session.commit()

        # Create a `Grid` with the same `.side_length` in the same `.city`.
        another_grid = db.Grid(city=grid.city, side_length=grid.side_length)
        db_session.add(another_grid)

        with pytest.raises(sa_exc.IntegrityError, match='duplicate key value'):
            db_session.commit()


class TestProperties:
    """Test properties in `Grid`."""

    def test_pixel_area(self, grid):
        """Test `Grid.pixel_area` property."""
        result = grid.pixel_area

        assert result == 1.0


class TestGridification:
    """Test the `Grid.gridify()` constructor."""

    @pytest.mark.no_cover
    def test_one_pixel_without_addresses(self, city):
        """At the very least, there must be one `Pixel` ...

        ... if the `side_length` is greater than both the
        horizontal and vertical distances of the viewport.

        This test case skips the `for`-loop inside `Grid.gridify()`.
        Interestingly, coverage.py does not see this.
        """
        city.addresses = []

        # `+1` as otherwise there would be a second pixel in one direction.
        side_length = max(city.total_x, city.total_y) + 1

        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert len(result.pixels) == 0  # noqa:WPS507

    def test_one_pixel_with_one_address(self, city, address):
        """At the very least, there must be one `Pixel` ...

        ... if the `side_length` is greater than both the
        horizontal and vertical distances of the viewport.
        """
        city.addresses = [address]

        # `+1` as otherwise there would be a second pixel in one direction.
        side_length = max(city.total_x, city.total_y) + 1

        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert len(result.pixels) == 1

    def test_one_pixel_with_two_addresses(self, city, make_address):
        """At the very least, there must be one `Pixel` ...

        ... if the `side_length` is greater than both the
        horizontal and vertical distances of the viewport.

        This test case is necessary as `test_one_pixel_with_one_address`
        does not have to re-use an already created `Pixel` object internally.
        """
        city.addresses = [make_address(), make_address()]

        # `+1` as otherwise there would be a second pixel in one direction.
        side_length = max(city.total_x, city.total_y) + 1

        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert len(result.pixels) == 1

    def test_one_pixel_with_address_too_far_south(self, city, address):
        """An `address` outside the `city`'s viewport is discarded."""
        # Move the `address` just below `city.southwest`.
        address.latitude = city.southwest.latitude - 0.1

        city.addresses = [address]

        # `+1` as otherwise there would be a second pixel in one direction.
        side_length = max(city.total_x, city.total_y) + 1

        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert len(result.pixels) == 0  # noqa:WPS507

    @pytest.mark.no_cover
    def test_one_pixel_with_address_too_far_west(self, city, address):
        """An `address` outside the `city`'s viewport is discarded.

        This test is a logical sibling to `test_one_pixel_with_address_too_far_south`
        and therefore redundant.
        """
        # Move the `address` just left to `city.southwest`.
        address.longitude = city.southwest.longitude - 0.1

        city.addresses = [address]

        # `+1` as otherwise there would be a second pixel in one direction.
        side_length = max(city.total_x, city.total_y) + 1

        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert len(result.pixels) == 0  # noqa:WPS507

    @pytest.mark.no_cover
    def test_four_pixels_with_two_addresses(self, city, make_address):
        """Two `Address` objects in distinct `Pixel` objects.

        This test is more of a sanity check.
        """
        # Create two `Address` objects in distinct `Pixel`s.
        city.addresses = [
            # One `Address` in the lower-left `Pixel`, ...
            make_address(latitude=48.8357377, longitude=2.2517412),
            # ... and another one in the upper-right one.
            make_address(latitude=48.8898312, longitude=2.4357622),
        ]

        side_length = max(city.total_x // 2, city.total_y // 2) + 1

        # By assumption of the test data.
        n_pixels_x = (city.total_x // side_length) + 1
        n_pixels_y = (city.total_y // side_length) + 1
        assert n_pixels_x * n_pixels_y == 4

        # Create a `Grid` with at most four `Pixel`s.
        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert len(result.pixels) == 2

    @pytest.mark.db
    @pytest.mark.no_cover
    @pytest.mark.parametrize('side_length', [250, 500, 1_000, 2_000, 4_000, 8_000])
    def test_make_random_grids(self, db_session, city, make_address, side_length):
        """With 100 random `Address` objects, a grid must have ...

        ... between 1 and a deterministic upper bound of `Pixel` objects.

        This test creates confidence that the created `Grid`
        objects adhere to the database constraints.
        """
        city.addresses = [make_address() for _ in range(100)]

        n_pixels_x = (city.total_x // side_length) + 1
        n_pixels_y = (city.total_y // side_length) + 1

        result = db.Grid.gridify(city=city, side_length=side_length)

        assert isinstance(result, db.Grid)
        assert 1 <= len(result.pixels) <= n_pixels_x * n_pixels_y

        db_session.add(result)
        db_session.commit()
