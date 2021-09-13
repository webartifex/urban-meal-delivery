"""A `Location` class to unify working with coordinates."""

from __future__ import annotations

from typing import Optional, Tuple

import utm


class Location:  # noqa:WPS214
    """A location represented in WGS84 and UTM coordinates.

    WGS84:
        - "conventional" system with latitude-longitude pairs
        - assumes earth is a sphere and models the location in 3D

    UTM:
        - the Universal Transverse Mercator system
        - projects WGS84 coordinates onto a 2D map
        - can be used for visualizations and calculations directly
        - distances are in meters

    Further info how WGS84 and UTM are related:
        https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system
    """

    def __init__(self, latitude: float, longitude: float) -> None:
        """Create a location from a WGS84-conforming `latitude`-`longitude` pair."""
        # The SQLAlchemy columns come as `Decimal`s due to the `DOUBLE_PRECISION`.
        self._latitude = float(latitude)
        self._longitude = float(longitude)

        easting, northing, zone, band = utm.from_latlon(self._latitude, self._longitude)

        # `.easting` and `.northing` as `int`s are precise enough.
        self._easting = int(easting)
        self._northing = int(northing)
        self._zone = zone
        self._band = band.upper()

        self._normalized_easting: Optional[int] = None
        self._normalized_northing: Optional[int] = None

    def __repr__(self) -> str:
        """A non-literal text representation in the UTM system.

        Convention is {ZONE} {EASTING} {NORTHING}.

        Example:
            `<Location: 17T 630084 4833438>'`
        """
        return f'<Location: {self.zone} {self.easting} {self.northing}>'  # noqa:WPS221

    @property
    def latitude(self) -> float:
        """The latitude of the location in degrees (WGS84).

        Between -90 and +90 degrees.
        """
        return self._latitude

    @property
    def longitude(self) -> float:
        """The longitude of the location in degrees (WGS84).

        Between -180 and +180 degrees.
        """
        return self._longitude

    @property
    def lat_lng(self) -> Tuple[float, float]:
        """The `.latitude` and `.longitude` as a 2-`tuple`."""
        return self._latitude, self._longitude

    @property
    def easting(self) -> int:
        """The easting of the location in meters (UTM)."""
        return self._easting

    @property
    def northing(self) -> int:
        """The northing of the location in meters (UTM)."""
        return self._northing

    @property
    def zone(self) -> str:
        """The UTM zone of the location."""
        return f'{self._zone}{self._band}'

    @property
    def zone_details(self) -> Tuple[int, str]:
        """The UTM zone of the location as the zone number and the band."""
        return self._zone, self._band

    def __eq__(self, other: object) -> bool:
        """Check if two `Location` objects are the same location."""
        if not isinstance(other, Location):
            return NotImplemented

        if self.zone != other.zone:
            raise ValueError('locations must be in the same zone, including the band')

        return (self.easting, self.northing) == (other.easting, other.northing)

    @property
    def x(self) -> int:  # noqa:WPS111
        """The `.easting` of the location in meters, relative to some origin.

        The origin, which defines the `(0, 0)` coordinate, is set with `.relate_to()`.
        """
        if self._normalized_easting is None:
            raise RuntimeError('an origin to relate to must be set first')

        return self._normalized_easting

    @property
    def y(self) -> int:  # noqa:WPS111
        """The `.northing` of the location in meters, relative to some origin.

        The origin, which defines the `(0, 0)` coordinate, is set with `.relate_to()`.
        """
        if self._normalized_northing is None:
            raise RuntimeError('an origin to relate to must be set first')

        return self._normalized_northing

    def relate_to(self, other: Location) -> None:
        """Make the origin in the lower-left corner relative to `other`.

        The `.x` and `.y` properties are the `.easting` and `.northing` values
        of `self` minus the ones from `other`. So, `.x` and `.y` make up a
        Cartesian coordinate system where the `other` origin is `(0, 0)`.

        To prevent semantic errors in calculations based on the `.x` and `.y`
        properties, the `other` origin may only be set once!
        """
        if self._normalized_easting is not None:
            raise RuntimeError('the `other` origin may only be set once')

        if not isinstance(other, Location):
            raise TypeError('`other` is not a `Location` object')

        if self.zone != other.zone:
            raise ValueError('`other` must be in the same zone, including the band')

        self._normalized_easting = self.easting - other.easting
        self._normalized_northing = self.northing - other.northing
