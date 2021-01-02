"""A `UTMCoordinate` class to unify working with coordinates."""

from __future__ import annotations

from typing import Optional

import utm


class UTMCoordinate:
    """A GPS location represented in UTM coordinates.

    For further info, we refer to this comprehensive article on the UTM system:
    https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system
    """

    # pylint:disable=too-many-instance-attributes

    def __init__(
        self, latitude: float, longitude: float, relative_to: UTMCoordinate = None,
    ) -> None:
        """Cast a WGS84-conforming `latitude`-`longitude` pair as UTM coordinates."""
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

        if relative_to:
            try:
                self.relate_to(relative_to)
            except TypeError:
                raise TypeError(
                    '`relative_to` must be a `UTMCoordinate` object',
                ) from None
            except ValueError:
                raise ValueError(
                    '`relative_to` must be in the same UTM zone as the `latitude`-`longitude` pair',  # noqa:E501
                ) from None

    def __repr__(self) -> str:
        """A non-literal text representation.

        Convention is {ZONE} {EASTING} {NORTHING}.

        Example:
            `<UTM: 17T 630084 4833438>'`
        """
        return f'<UTM: {self.zone} {self.easting} {self.northing}>'  # noqa:WPS221

    @property
    def easting(self) -> int:
        """The easting of the location in meters."""
        return self._easting

    @property
    def northing(self) -> int:
        """The northing of the location in meters."""
        return self._northing

    @property
    def zone(self) -> str:
        """The UTM zone of the location."""
        return f'{self._zone}{self._band}'

    def __eq__(self, other: object) -> bool:
        """Check if two `UTMCoordinate` objects are the same location."""
        if not isinstance(other, UTMCoordinate):
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

    def relate_to(self, other: UTMCoordinate) -> None:
        """Make the origin in the lower-left corner relative to `other`.

        The `.x` and `.y` properties are the `.easting` and `.northing` values
        of `self` minus the ones from `other`. So, `.x` and `.y` make up a
        Cartesian coordinate system where the `other` origin is `(0, 0)`.

        This method is implicitly called by `.__init__()` if that is called
        with a `relative_to` argument.

        To prevent semantic errors in calculations based on the `.x` and `.y`
        properties, the `other` origin may only be set once!
        """
        if self._normalized_easting is not None:
            raise RuntimeError('the `other` origin may only be set once')

        if not isinstance(other, UTMCoordinate):
            raise TypeError('`other` is not a `UTMCoordinate` object')

        if self.zone != other.zone:
            raise ValueError('`other` must be in the same zone, including the band')

        self._normalized_easting = self.easting - other.easting
        self._normalized_northing = self.northing - other.northing
