"""Factory to create `Restaurant` instances."""

import factory
import faker
from factory import alchemy

from tests.db.fake_data.factories import utils
from urban_meal_delivery import db


_restaurant_names = faker.Faker()


class RestaurantFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Restaurant` model."""

    class Meta:
        model = db.Restaurant
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    created_at = factory.LazyFunction(utils.early_in_the_morning)
    name = factory.LazyFunction(
        lambda: f"{_restaurant_names.first_name()}'s Restaurant",
    )
    # address -> set by the `make_restaurant` fixture as there is only one `city`
    estimated_prep_duration = 1000
