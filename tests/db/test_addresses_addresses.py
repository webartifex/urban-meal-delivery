"""Test the ORM's `DistanceMatrix` model."""

import json

import googlemaps
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
        address.location.lat_lng, another_address.location.lat_lng,
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


@pytest.mark.db
class TestFromAddresses:
    """Test the alternative constructor `DistanceMatrix.from_addresses()`."""

    @pytest.fixture
    def _prepare_db(self, db_session, address):
        """Put the `address` into the database.

        `Address`es must be in the database as otherwise the `.city_id` column
        cannot be resolved in `DistanceMatrix.from_addresses()`.
        """
        db_session.add(address)

    @pytest.mark.usefixtures('_prepare_db')
    def test_make_distance_matrix_instance(
        self, db_session, address, another_address,
    ):
        """Test instantiation of a new `DistanceMatrix` instance."""
        assert db_session.query(db.DistanceMatrix).count() == 0

        db.DistanceMatrix.from_addresses(address, another_address)

        assert db_session.query(db.DistanceMatrix).count() == 1

    @pytest.mark.usefixtures('_prepare_db')
    def test_make_the_same_distance_matrix_instance_twice(
        self, db_session, address, another_address,
    ):
        """Test instantiation of a new `DistanceMatrix` instance."""
        assert db_session.query(db.DistanceMatrix).count() == 0

        db.DistanceMatrix.from_addresses(address, another_address)

        assert db_session.query(db.DistanceMatrix).count() == 1

        db.DistanceMatrix.from_addresses(another_address, address)

        assert db_session.query(db.DistanceMatrix).count() == 1

    @pytest.mark.usefixtures('_prepare_db')
    def test_structure_of_return_value(self, db_session, address, another_address):
        """Test instantiation of a new `DistanceMatrix` instance."""
        results = db.DistanceMatrix.from_addresses(address, another_address)

        assert isinstance(results, list)

    @pytest.mark.usefixtures('_prepare_db')
    def test_instances_must_have_air_distance(
        self, db_session, address, another_address,
    ):
        """Test instantiation of a new `DistanceMatrix` instance."""
        distances = db.DistanceMatrix.from_addresses(address, another_address)

        result = distances[0]

        assert result.air_distance is not None

    @pytest.mark.usefixtures('_prepare_db')
    def test_do_not_sync_instances_with_google_maps(
        self, db_session, address, another_address,
    ):
        """Test instantiation of a new `DistanceMatrix` instance."""
        distances = db.DistanceMatrix.from_addresses(address, another_address)

        result = distances[0]

        assert result.bicycle_distance is None
        assert result.bicycle_duration is None

    @pytest.mark.usefixtures('_prepare_db')
    def test_sync_instances_with_google_maps(
        self, db_session, address, another_address, monkeypatch,
    ):
        """Test instantiation of a new `DistanceMatrix` instance."""

        def sync(self):
            self.bicycle_distance = 1.25 * self.air_distance
            self.bicycle_duration = 300

        monkeypatch.setattr(db.DistanceMatrix, 'sync_with_google_maps', sync)

        distances = db.DistanceMatrix.from_addresses(
            address, another_address, google_maps=True,
        )

        result = distances[0]

        assert result.bicycle_distance is not None
        assert result.bicycle_duration is not None

    @pytest.mark.usefixtures('_prepare_db')
    def test_one_distance_for_two_addresses(self, db_session, address, another_address):
        """Test instantiation of a new `DistanceMatrix` instance."""
        result = len(db.DistanceMatrix.from_addresses(address, another_address))

        assert result == 1

    @pytest.mark.usefixtures('_prepare_db')
    def test_two_distances_for_three_addresses(self, db_session, make_address):
        """Test instantiation of a new `DistanceMatrix` instance."""
        result = len(
            db.DistanceMatrix.from_addresses(*[make_address() for _ in range(3)]),
        )

        assert result == 3

    @pytest.mark.usefixtures('_prepare_db')
    def test_six_distances_for_four_addresses(self, db_session, make_address):
        """Test instantiation of a new `DistanceMatrix` instance."""
        result = len(
            db.DistanceMatrix.from_addresses(*[make_address() for _ in range(4)]),
        )

        assert result == 6


@pytest.mark.db
class TestSyncWithGoogleMaps:
    """Test the `DistanceMatrix.sync_with_google_maps()` method."""

    @pytest.fixture
    def api_response(self):
        """A typical (shortened) response by the Google Maps Directions API."""
        return [  # noqa:ECE001
            {
                'bounds': {
                    'northeast': {'lat': 44.8554284, 'lng': -0.5652398},
                    'southwest': {'lat': 44.8342256, 'lng': -0.5708206},
                },
                'copyrights': 'Map data ©2021',
                'legs': [
                    {
                        'distance': {'text': '3.0 km', 'value': 2969},
                        'duration': {'text': '10 mins', 'value': 596},
                        'end_address': '13 Place Paul et Jean Paul Avisseau, ...',
                        'end_location': {'lat': 44.85540839999999, 'lng': -0.5672105},
                        'start_address': '59 Rue Saint-François, 33000 Bordeaux, ...',
                        'start_location': {'lat': 44.8342256, 'lng': -0.570372},
                        'steps': [
                            {
                                'distance': {'text': '0.1 km', 'value': 108},
                                'duration': {'text': '1 min', 'value': 43},
                                'end_location': {
                                    'lat': 44.83434380000001,
                                    'lng': -0.5690105999999999,
                                },
                                'html_instructions': 'Head <b>east</b> on <b> ...',
                                'polyline': {'points': '}tspGxknBKcDIkB'},
                                'start_location': {'lat': 44.8342256, 'lng': -0.57032},
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.1 km', 'value': 115},
                                'duration': {'text': '1 min', 'value': 22},
                                'end_location': {'lat': 44.8353651, 'lng': -0.569199},
                                'html_instructions': 'Turn <b>left</b> onto <b> ...',
                                'maneuver': 'turn-left',
                                'polyline': {'points': 'suspGhcnBc@JE@_@DiAHA?w@F'},
                                'start_location': {
                                    'lat': 44.83434380000001,
                                    'lng': -0.5690105999999999,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.3 km', 'value': 268},
                                'duration': {'text': '1 min', 'value': 59},
                                'end_location': {'lat': 44.8362675, 'lng': -0.5660914},
                                'html_instructions': 'Turn <b>right</b> onto <b> ...',
                                'maneuver': 'turn-right',
                                'polyline': {
                                    'points': 'a|spGndnBEYEQKi@Mi@Is@CYCOE]CQIq@ ...',
                                },
                                'start_location': {'lat': 44.8353651, 'lng': -0.56919},
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.1 km', 'value': 95},
                                'duration': {'text': '1 min', 'value': 29},
                                'end_location': {'lat': 44.8368458, 'lng': -0.5652398},
                                'html_instructions': 'Slight <b>left</b> onto <b> ...',
                                'maneuver': 'turn-slight-left',
                                'polyline': {
                                    'points': 'uatpG`qmBg@aAGM?ACE[k@CICGACEGCCAAEAG?',
                                },
                                'start_location': {
                                    'lat': 44.8362675,
                                    'lng': -0.5660914,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '23 m', 'value': 23},
                                'duration': {'text': '1 min', 'value': 4},
                                'end_location': {'lat': 44.83697, 'lng': -0.5654425},
                                'html_instructions': 'Slight <b>left</b> to stay ...',
                                'maneuver': 'turn-slight-left',
                                'polyline': {
                                    'points': 'ietpGvkmBA@C?CBCBEHA@AB?B?B?B?@',
                                },
                                'start_location': {
                                    'lat': 44.8368458,
                                    'lng': -0.5652398,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.2 km', 'value': 185},
                                'duration': {'text': '1 min', 'value': 23},
                                'end_location': {'lat': 44.8382126, 'lng': -0.5669969},
                                'html_instructions': 'Take the ramp to <b>Le Lac ...',
                                'polyline': {
                                    'points': 'aftpG~lmBY^[^sAdB]`@CDKLQRa@h@A@IZ',
                                },
                                'start_location': {'lat': 44.83697, 'lng': -0.5654425},
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.3 km', 'value': 253},
                                'duration': {'text': '1 min', 'value': 43},
                                'end_location': {'lat': 44.840163, 'lng': -0.5686525},
                                'html_instructions': 'Merge onto <b>Quai Richelieu</b>',
                                'maneuver': 'merge',
                                'polyline': {
                                    'points': 'ymtpGvvmBeAbAe@b@_@ZUN[To@f@e@^A?g ...',
                                },
                                'start_location': {
                                    'lat': 44.8382126,
                                    'lng': -0.5669969,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.1 km', 'value': 110},
                                'duration': {'text': '1 min', 'value': 21},
                                'end_location': {'lat': 44.841079, 'lng': -0.5691835},
                                'html_instructions': 'Continue onto <b>Quai de la ...',
                                'polyline': {'points': '_ztpG`anBUNQLULUJOHMFKDWN'},
                                'start_location': {'lat': 44.840163, 'lng': -0.56865},
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.3 km', 'value': 262},
                                'duration': {'text': '1 min', 'value': 44},
                                'end_location': {'lat': 44.8433375, 'lng': -0.5701161},
                                'html_instructions': 'Continue onto <b>Quai du ...',
                                'polyline': {
                                    'points': 'w_upGjdnBeBl@sBn@gA^[JIBc@Nk@Nk@L',
                                },
                                'start_location': {'lat': 44.841079, 'lng': -0.56915},
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.6 km', 'value': 550},
                                'duration': {'text': '2 mins', 'value': 97},
                                'end_location': {
                                    'lat': 44.84822339999999,
                                    'lng': -0.5705307,
                                },
                                'html_instructions': 'Continue onto <b>Quai ...',
                                'polyline': {
                                    'points': '{mupGfjnBYFI@IBaAPUD{AX}@NK@]Fe@H ...',
                                },
                                'start_location': {
                                    'lat': 44.8433375,
                                    'lng': -0.5701161,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.5 km', 'value': 508},
                                'duration': {'text': '1 min', 'value': 87},
                                'end_location': {'lat': 44.8523224, 'lng': -0.5678223},
                                'html_instructions': 'Continue onto ...',
                                'polyline': {
                                    'points': 'klvpGxlnBWEUGWGSGMEOEOE[KMEQGIA] ...',
                                },
                                'start_location': {
                                    'lat': 44.84822339999999,
                                    'lng': -0.5705307,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '28 m', 'value': 28},
                                'duration': {'text': '1 min', 'value': 45},
                                'end_location': {
                                    'lat': 44.85245620000001,
                                    'lng': -0.5681259,
                                },
                                'html_instructions': 'Turn <b>left</b> onto <b> ...',
                                'maneuver': 'turn-left',
                                'polyline': {'points': '_fwpGz{mBGLADGPCFEN'},
                                'start_location': {
                                    'lat': 44.8523224,
                                    'lng': -0.5678223,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.2 km', 'value': 176},
                                'duration': {'text': '1 min', 'value': 31},
                                'end_location': {'lat': 44.8536857, 'lng': -0.5667282},
                                'html_instructions': 'Turn <b>right</b> onto <b> ...',
                                'maneuver': 'turn-right',
                                'polyline': {
                                    'points': '{fwpGx}mB_@c@mAuAOQi@m@m@y@_@c@',
                                },
                                'start_location': {
                                    'lat': 44.85245620000001,
                                    'lng': -0.5681259,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.2 km', 'value': 172},
                                'duration': {'text': '1 min', 'value': 28},
                                'end_location': {'lat': 44.8547766, 'lng': -0.5682825},
                                'html_instructions': 'Turn <b>left</b> onto <b> ... ',
                                'maneuver': 'turn-left',
                                'polyline': {'points': 'qnwpG`umBW`@UkDtF'},
                                'start_location': {
                                    'lat': 44.8536857,
                                    'lng': -0.5667282,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '0.1 km', 'value': 101},
                                'duration': {'text': '1 min', 'value': 17},
                                'end_location': {'lat': 44.8554284, 'lng': -0.5673822},
                                'html_instructions': 'Turn <b>right</b> onto ...',
                                'maneuver': 'turn-right',
                                'polyline': {'points': 'kuwpGv~mBa@q@cA_B[a@'},
                                'start_location': {
                                    'lat': 44.8547766,
                                    'lng': -0.5682825,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                            {
                                'distance': {'text': '15 m', 'value': 15},
                                'duration': {'text': '1 min', 'value': 3},
                                'end_location': {
                                    'lat': 44.85540839999999,
                                    'lng': -0.5672105,
                                },
                                'html_instructions': 'Turn <b>right</b> onto <b> ...',
                                'maneuver': 'turn-right',
                                'polyline': {'points': 'mywpGbymBBC@C?E?C?E?EAC'},
                                'start_location': {
                                    'lat': 44.8554284,
                                    'lng': -0.5673822,
                                },
                                'travel_mode': 'BICYCLING',
                            },
                        ],
                        'traffic_speed_entry': [],
                        'via_waypoint': [],
                    },
                ],
                'overview_polyline': {
                    'points': '}tspGxknBUoGi@LcDVe@_CW{Ba@sC[eA_@} ...',
                },
                'summary': 'Quai des Chartrons',
                'warnings': ['Bicycling directions are in beta ...'],
                'waypoint_order': [],
            },
        ]

    @pytest.fixture
    def _fake_google_api(self, api_response, monkeypatch):
        """Patch out the call to the Google Maps Directions API."""

        def directions(self, *args, **kwargs):
            return api_response

        monkeypatch.setattr(googlemaps.Client, 'directions', directions)

    @pytest.mark.usefixtures('_fake_google_api')
    def test_sync_instances_with_google_maps(self, db_session, assoc):
        """Call the method for a `DistanceMatrix` object without Google data."""
        assoc.bicycle_distance = None
        assoc.bicycle_duration = None
        assoc.directions = None

        assoc.sync_with_google_maps()

        assert assoc.bicycle_distance == 2_969
        assert assoc.bicycle_duration == 596
        assert assoc.directions is not None

    @pytest.mark.usefixtures('_fake_google_api')
    def test_repeated_sync_instances_with_google_maps(self, db_session, assoc):
        """Call the method for a `DistanceMatrix` object with Google data.

        That call should immediately return without changing any data.

        We use the `assoc`'s "Google" data from above.
        """
        old_distance = assoc.bicycle_distance
        old_duration = assoc.bicycle_duration
        old_directions = assoc.directions

        assoc.sync_with_google_maps()

        assert assoc.bicycle_distance is old_distance
        assert assoc.bicycle_duration is old_duration
        assert assoc.directions is old_directions


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
