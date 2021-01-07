"""Provide the ORM models and a connection to the database."""

from urban_meal_delivery.db.addresses import Address
from urban_meal_delivery.db.addresses_pixels import AddressPixelAssociation
from urban_meal_delivery.db.cities import City
from urban_meal_delivery.db.connection import connection
from urban_meal_delivery.db.connection import engine
from urban_meal_delivery.db.connection import session
from urban_meal_delivery.db.couriers import Courier
from urban_meal_delivery.db.customers import Customer
from urban_meal_delivery.db.forecasts import Forecast
from urban_meal_delivery.db.grids import Grid
from urban_meal_delivery.db.meta import Base
from urban_meal_delivery.db.orders import Order
from urban_meal_delivery.db.pixels import Pixel
from urban_meal_delivery.db.restaurants import Restaurant
