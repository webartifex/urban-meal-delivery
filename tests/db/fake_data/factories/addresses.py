"""Factory to create `Address` instances."""

import random
import string

import factory
from factory import alchemy

from tests.db.fake_data.factories import utils
from urban_meal_delivery import db


class AddressFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Address` model."""

    class Meta:
        model = db.Address
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    created_at = factory.LazyFunction(utils.early_in_the_morning)

    # When testing, all addresses are considered primary ones.
    # As non-primary addresses have no different behavior and
    # the property is only kept from the original dataset for
    # completeness sake, that is ok to do.
    primary_id = factory.LazyAttribute(lambda obj: obj.id)

    # Mimic a Google Maps Place ID with just random characters.
    place_id = factory.LazyFunction(
        lambda: ''.join(random.choice(string.ascii_lowercase) for _ in range(20)),
    )

    # Place the addresses somewhere in downtown Paris.
    latitude = factory.Faker('coordinate', center=48.855, radius=0.01)
    longitude = factory.Faker('coordinate', center=2.34, radius=0.03)
    # city -> set by the `make_address` fixture as there is only one `city`
    city_name = 'Paris'
    zip_code = factory.LazyFunction(lambda: random.randint(75001, 75020))
    street = factory.Faker('street_address', locale='fr_FR')
