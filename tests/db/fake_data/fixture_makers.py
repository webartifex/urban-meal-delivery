"""Fixture factories for testing the ORM layer with fake data."""

import pytest

from tests.db.fake_data import factories


@pytest.fixture
def make_address(city):
    """Replaces `AddressFactory.build()`: Create an `Address` in the `city`."""
    # Reset the identifiers before every test.
    factories.AddressFactory.reset_sequence(1)

    def func(**kwargs):
        """Create an `Address` object in the `city`."""
        return factories.AddressFactory.build(city=city, **kwargs)

    return func


@pytest.fixture
def make_courier():
    """Replaces `CourierFactory.build()`: Create a `Courier`."""
    # Reset the identifiers before every test.
    factories.CourierFactory.reset_sequence(1)

    def func(**kwargs):
        """Create a new `Courier` object."""
        return factories.CourierFactory.build(**kwargs)

    return func


@pytest.fixture
def make_customer():
    """Replaces `CustomerFactory.build()`: Create a `Customer`."""
    # Reset the identifiers before every test.
    factories.CustomerFactory.reset_sequence(1)

    def func(**kwargs):
        """Create a new `Customer` object."""
        return factories.CustomerFactory.build(**kwargs)

    return func


@pytest.fixture
def make_restaurant(make_address):
    """Replaces `RestaurantFactory.build()`: Create a `Restaurant`."""
    # Reset the identifiers before every test.
    factories.RestaurantFactory.reset_sequence(1)

    def func(address=None, **kwargs):
        """Create a new `Restaurant` object.

        If no `address` is provided, a new `Address` is created.
        """
        if address is None:
            address = make_address()

        return factories.RestaurantFactory.build(address=address, **kwargs)

    return func


@pytest.fixture
def make_order(make_address, make_courier, make_customer, make_restaurant):
    """Replaces `OrderFactory.build()`: Create a `Order`."""
    # Reset the identifiers before every test.
    factories.AdHocOrderFactory.reset_sequence(1)

    def func(scheduled=False, restaurant=None, courier=None, **kwargs):
        """Create a new `Order` object.

        Each `Order` is made by a new `Customer` with a unique `Address` for delivery.

        Args:
            scheduled: if an `Order` is a pre-order
            restaurant: who receives the `Order`; defaults to a new `Restaurant`
            courier: who delivered the `Order`; defaults to a new `Courier`
            kwargs: additional keyword arguments forwarded to the `OrderFactory`

        Returns:
            order
        """
        if scheduled:
            factory_cls = factories.ScheduledOrderFactory
        else:
            factory_cls = factories.AdHocOrderFactory

        if restaurant is None:
            restaurant = make_restaurant()
        if courier is None:
            courier = make_courier()

        return factory_cls.build(
            customer=make_customer(),  # assume a unique `Customer` per order
            restaurant=restaurant,
            courier=courier,
            pickup_address=restaurant.address,  # no `Address` history
            delivery_address=make_address(),  # unique `Customer` => new `Address`
            **kwargs,
        )

    return func
