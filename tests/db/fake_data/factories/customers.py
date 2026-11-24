"""Factory to create `Customers` instances."""

import factory
from factory import alchemy

from velofy import db


class CustomerFactory(alchemy.SQLAlchemyModelFactory):
    """Create instances of the `db.Customer` model."""

    class Meta:
        model = db.Customer
        sqlalchemy_get_or_create = ('id',)

    id = factory.Sequence(lambda num: num)  # noqa:WPS125
