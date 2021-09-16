"""Factories to create instances for the SQLAlchemy models."""

from tests.db.fake_data.factories.addresses import AddressFactory
from tests.db.fake_data.factories.couriers import CourierFactory
from tests.db.fake_data.factories.customers import CustomerFactory
from tests.db.fake_data.factories.orders import AdHocOrderFactory
from tests.db.fake_data.factories.orders import ReplayedOrderFactory
from tests.db.fake_data.factories.orders import ScheduledOrderFactory
from tests.db.fake_data.factories.restaurants import RestaurantFactory
