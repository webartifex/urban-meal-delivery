"""Factory to create `Courier` instances."""


import factory
from factory import alchemy

from tests.db.fake_data.factories import utils
from urban_meal_delivery import db


class CourierFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Courier` model."""

    class Meta:
        model = db.Courier
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
    created_at = factory.LazyFunction(utils.early_in_the_morning)
    vehicle = 'bicycle'
    historic_speed = 7.89
    capacity = 100
    pay_per_hour = 750
    pay_per_order = 200
