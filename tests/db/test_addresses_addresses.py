"""Test the ORM's `DistanceMatrix` model."""

import json

import pytest
import sqlalchemy as sqla
from geopy import distance
from sqlalchemy import exc as sa_exc

from urban_meal_delivery import db
from urban_meal_delivery.db import utils


@pytest.fixture
def another_address(make_address):
    """Another `Address` object in the `city`."""
    return make_address()


@pytest.fixture
def assoc(address, another_address, make_address):
    """An association between `address` and `another_address`."""
    air_distance = distance.great_circle(  # noqa:WPS317
        (address.latitude, address.longitude),
        (another_address.latitude, another_address.longitude),
    ).meters

    # We put 5 latitude-longitude pairs as the "path" from
    # `.first_address` to `.second_address`.
    directions = json.dumps(
        [
            (float(addr.latitude), float(addr.longitude))
            for addr in (make_address() for _ in range(5))  # noqa:WPS335
        ],
    )

    return db.DistanceMatrix(
        first_address=address,
        second_address=another_address,
        air_distance=round(air_distance),
        bicycle_distance=round(1.25 * air_distance),
        bicycle_duration=300,
        directions=directions,
    )


class TestSpecialMethods:
    """Test special methods in `DistanceMatrix`."""

    def test_create_an_address_address_association(self, assoc):
        """Test instantiation of a new `DistanceMatrix` object."""
        assert assoc is not None


@pytest.mark.db
@pytest.mark.no_cover
class TestConstraints:
    """Test the database constraints defined in `DistanceMatrix`."""

    def test_insert_into_database(self, db_session, assoc):
        """Insert an instance into the (empty) database."""
        assert db_session.query(db.DistanceMatrix).count() == 0

        db_session.add(assoc)
        db_session.commit()

        assert db_session.query(db.DistanceMatrix).count() == 1

    def test_delete_a_referenced_first_address(self, db_session, assoc):
        """Remove a record that is referenced with a FK."""
        db_session.add(assoc)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Address).where(db.Address.id == assoc.first_address.id)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_addresses_to_addresses_via_first_address',  # shortened
        ):
            db_session.execute(stmt)

    def test_delete_a_referenced_second_address(self, db_session, assoc):
        """Remove a record that is referenced with a FK."""
        db_session.add(assoc)
        db_session.commit()

        # Must delete without ORM as otherwise an UPDATE statement is emitted.
        stmt = sqla.delete(db.Address).where(db.Address.id == assoc.second_address.id)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_addresses_to_addresses_via_second_address',  # shortened
        ):
            db_session.execute(stmt)

    def test_reference_an_invalid_city(self, db_session, address, another_address):
        """Insert a record with an invalid foreign key."""
        db_session.add(address)
        db_session.add(another_address)
        db_session.commit()

        # Must insert without ORM as otherwise SQLAlchemy figures out
        # that something is wrong before any query is sent to the database.
        stmt = sqla.insert(db.DistanceMatrix).values(
            first_address_id=address.id,
            second_address_id=another_address.id,
            city_id=999,
            air_distance=123,
        )

        with pytest.raises(
            sa_exc.IntegrityError,
            match='fk_addresses_addresses_to_addresses_via_first_address',  # shortened
        ):
            db_session.execute(stmt)

    def test_redundant_addresses(self, db_session, assoc):
        """Insert a record that violates a unique constraint."""
        db_session.add(assoc)
        db_session.commit()

        # Must insert without ORM as otherwise SQLAlchemy figures out
        # that something is wrong before any query is sent to the database.
        stmt = sqla.insert(db.DistanceMatrix).values(
            first_address_id=assoc.first_address.id,
            second_address_id=assoc.second_address.id,
            city_id=assoc.city_id,
            air_distance=assoc.air_distance,
        )

        with pytest.raises(sa_exc.IntegrityError, match='duplicate key value'):
            db_session.execute(stmt)

    def test_symmetric_addresses(self, db_session, assoc):
        """Insert a record that violates a check constraint."""
        db_session.add(assoc)
        db_session.commit()

        another_assoc = db.DistanceMatrix(
            first_address=assoc.second_address,
            second_address=assoc.first_address,
            air_distance=assoc.air_distance,
        )
        db_session.add(another_assoc)

        with pytest.raises(
            sa_exc.IntegrityError,
            match='ck_addresses_addresses_on_distances_are_symmetric_for_bicycles',
        ):
            db_session.commit()

    def test_negative_air_distance(self, db_session, assoc):
        """Insert an instance with invalid data."""
        assoc.air_distance = -1
        db_session.add(assoc)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_air_distance'):
            db_session.commit()

    def test_air_distance_too_large(self, db_session, assoc):
        """Insert an instance with invalid data."""
        assoc.air_distance = 20_000
        assoc.bicycle_distance = 21_000
        db_session.add(assoc)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_air_distance'):
            db_session.commit()

    def test_bicycle_distance_too_large(self, db_session, assoc):
        """Insert an instance with invalid data."""
        assoc.bicycle_distance = 25_000
        db_session.add(assoc)

        with pytest.raises(sa_exc.IntegrityError, match='realistic_bicycle_distance'):
            db_session.commit()

    def test_air_distance_shorter_than_bicycle_distance(self, db_session, assoc):
        """Insert an instance with invalid data."""
        assoc.bicycle_distance = round(0.75 * assoc.air_distance)
        db_session.add(assoc)

        with pytest.raises(sa_exc.IntegrityError, match='air_distance_is_shortest'):
            db_session.commit()

    @pytest.mark.parametrize('duration', [-1, 3601])
    def test_unrealistic_bicycle_travel_time(self, db_session, assoc, duration):
        """Insert an instance with invalid data."""
        assoc.bicycle_duration = duration
        db_session.add(assoc)

        with pytest.raises(
            sa_exc.IntegrityError, match='realistic_bicycle_travel_time',
        ):
            db_session.commit()


class TestProperties:
    """Test properties in `DistanceMatrix`."""

    def test_path_structure(self, assoc):
        """Test `DistanceMatrix.path` property."""
        result = assoc.path

        assert isinstance(result, list)
        assert isinstance(result[0], utils.Location)

    def test_path_content(self, assoc):
        """Test `DistanceMatrix.path` property."""
        result = assoc.path

        assert len(result) == 5  # = 5 inner points, excluding start and end

    def test_path_is_cached(self, assoc):
        """Test `DistanceMatrix.path` property."""
        result1 = assoc.path
        result2 = assoc.path

        assert result1 is result2
