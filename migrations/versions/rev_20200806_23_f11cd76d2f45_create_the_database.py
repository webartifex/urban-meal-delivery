"""Create the database from scratch.

Revision: #f11cd76d2f45 at 2020-08-06 23:24:32
"""

import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from urban_meal_delivery import configuration


revision = 'f11cd76d2f45'
down_revision = None
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision f11cd76d2f45."""
    op.execute(f'CREATE SCHEMA {config.CLEAN_SCHEMA};')
    op.create_table(  # noqa:ECE001
        'cities',
        sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column('name', sa.Unicode(length=10), nullable=False),
        sa.Column('kml', sa.UnicodeText(), nullable=False),
        sa.Column('center_latitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('center_longitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('northeast_latitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('northeast_longitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('southwest_latitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('southwest_longitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('initial_zoom', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cities')),
        *(
            [  # noqa:WPS504
                sa.ForeignKeyConstraint(
                    ['id'],
                    [f'{config.ORIGINAL_SCHEMA}.cities.id'],
                    name=op.f('pk_cities_sanity'),
                    onupdate='RESTRICT',
                    ondelete='RESTRICT',
                ),
            ]
            if not config.TESTING
            else []
        ),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_table(  # noqa:ECE001
        'couriers',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('vehicle', sa.Unicode(length=10), nullable=False),
        sa.Column('speed', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('capacity', sa.SmallInteger(), nullable=False),
        sa.Column('pay_per_hour', sa.SmallInteger(), nullable=False),
        sa.Column('pay_per_order', sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "vehicle IN ('bicycle', 'motorcycle')",
            name=op.f('ck_couriers_on_available_vehicle_types'),
        ),
        sa.CheckConstraint(
            '0 <= capacity AND capacity <= 200',
            name=op.f('ck_couriers_on_capacity_under_200_liters'),
        ),
        sa.CheckConstraint(
            '0 <= pay_per_hour AND pay_per_hour <= 1500',
            name=op.f('ck_couriers_on_realistic_pay_per_hour'),
        ),
        sa.CheckConstraint(
            '0 <= pay_per_order AND pay_per_order <= 650',
            name=op.f('ck_couriers_on_realistic_pay_per_order'),
        ),
        sa.CheckConstraint(
            '0 <= speed AND speed <= 30', name=op.f('ck_couriers_on_realistic_speed'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_couriers')),
        *(
            [  # noqa:WPS504
                sa.ForeignKeyConstraint(
                    ['id'],
                    [f'{config.ORIGINAL_SCHEMA}.couriers.id'],
                    name=op.f('pk_couriers_sanity'),
                    onupdate='RESTRICT',
                    ondelete='RESTRICT',
                ),
            ]
            if not config.TESTING
            else []
        ),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_customers')),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_table(  # noqa:ECE001
        'addresses',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('primary_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('place_id', sa.Unicode(length=120), nullable=False),
        sa.Column('latitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('longitude', postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column('city_id', sa.SmallInteger(), nullable=False),
        sa.Column('city', sa.Unicode(length=25), nullable=False),
        sa.Column('zip_code', sa.Integer(), nullable=False),
        sa.Column('street', sa.Unicode(length=80), nullable=False),
        sa.Column('floor', sa.SmallInteger(), nullable=True),
        sa.CheckConstraint(
            '-180 <= longitude AND longitude <= 180',
            name=op.f('ck_addresses_on_longitude_between_180_degrees'),
        ),
        sa.CheckConstraint(
            '-90 <= latitude AND latitude <= 90',
            name=op.f('ck_addresses_on_latitude_between_90_degrees'),
        ),
        sa.CheckConstraint(
            '0 <= floor AND floor <= 40', name=op.f('ck_addresses_on_realistic_floor'),
        ),
        sa.CheckConstraint(
            '30000 <= zip_code AND zip_code <= 99999',
            name=op.f('ck_addresses_on_valid_zip_code'),
        ),
        sa.ForeignKeyConstraint(
            ['city_id'],
            [f'{config.CLEAN_SCHEMA}.cities.id'],
            name=op.f('fk_addresses_to_cities_via_city_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['primary_id'],
            [f'{config.CLEAN_SCHEMA}.addresses.id'],
            name=op.f('fk_addresses_to_addresses_via_primary_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_addresses')),
        *(
            [  # noqa:WPS504
                sa.ForeignKeyConstraint(
                    ['id'],
                    [f'{config.ORIGINAL_SCHEMA}.addresses.id'],
                    name=op.f('pk_addresses_sanity'),
                    onupdate='RESTRICT',
                    ondelete='RESTRICT',
                ),
            ]
            if not config.TESTING
            else []
        ),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_addresses_on_city_id'),
        'addresses',
        ['city_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_addresses_on_place_id'),
        'addresses',
        ['place_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_addresses_on_primary_id'),
        'addresses',
        ['primary_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_addresses_on_zip_code'),
        'addresses',
        ['zip_code'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_table(  # noqa:ECE001
        'restaurants',
        sa.Column('id', sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=45), nullable=False),
        sa.Column('address_id', sa.Integer(), nullable=False),
        sa.Column('estimated_prep_duration', sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 2400',
            name=op.f('ck_restaurants_on_realistic_estimated_prep_duration'),
        ),
        sa.ForeignKeyConstraint(
            ['address_id'],
            [f'{config.CLEAN_SCHEMA}.addresses.id'],
            name=op.f('fk_restaurants_to_addresses_via_address_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_restaurants')),
        *(
            [  # noqa:WPS504
                sa.ForeignKeyConstraint(
                    ['id'],
                    [f'{config.ORIGINAL_SCHEMA}.businesses.id'],
                    name=op.f('pk_restaurants_sanity'),
                    onupdate='RESTRICT',
                    ondelete='RESTRICT',
                ),
            ]
            if not config.TESTING
            else []
        ),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_restaurants_on_address_id'),
        'restaurants',
        ['address_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_table(  # noqa:ECE001
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('delivery_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('placed_at', sa.DateTime(), nullable=False),
        sa.Column('ad_hoc', sa.Boolean(), nullable=False),
        sa.Column('scheduled_delivery_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_delivery_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('first_estimated_delivery_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled', sa.Boolean(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('sub_total', sa.Integer(), nullable=False),
        sa.Column('delivery_fee', sa.SmallInteger(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.SmallInteger(), nullable=False),
        sa.Column('restaurant_notified_at', sa.DateTime(), nullable=True),
        sa.Column('restaurant_notified_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('restaurant_confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('restaurant_confirmed_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('estimated_prep_duration', sa.Integer(), nullable=True),
        sa.Column('estimated_prep_duration_corrected', sa.Boolean(), nullable=True),
        sa.Column('estimated_prep_buffer', sa.Integer(), nullable=False),
        sa.Column('courier_id', sa.Integer(), nullable=True),
        sa.Column('dispatch_at', sa.DateTime(), nullable=True),
        sa.Column('dispatch_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('courier_notified_at', sa.DateTime(), nullable=True),
        sa.Column('courier_notified_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('courier_accepted_at', sa.DateTime(), nullable=True),
        sa.Column('courier_accepted_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('utilization', sa.SmallInteger(), nullable=False),
        sa.Column('pickup_address_id', sa.Integer(), nullable=False),
        sa.Column('reached_pickup_at', sa.DateTime(), nullable=True),
        sa.Column('pickup_at', sa.DateTime(), nullable=True),
        sa.Column('pickup_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('pickup_not_confirmed', sa.Boolean(), nullable=True),
        sa.Column('left_pickup_at', sa.DateTime(), nullable=True),
        sa.Column('left_pickup_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('delivery_address_id', sa.Integer(), nullable=False),
        sa.Column('reached_delivery_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_at_corrected', sa.Boolean(), nullable=True),
        sa.Column('delivery_not_confirmed', sa.Boolean(), nullable=True),
        sa.Column('courier_waited_at_delivery', sa.Boolean(), nullable=True),
        sa.Column('logged_delivery_distance', sa.SmallInteger(), nullable=True),
        sa.Column('logged_avg_speed', postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column('logged_avg_speed_distance', sa.SmallInteger(), nullable=True),
        sa.CheckConstraint(
            '0 <= estimated_prep_buffer AND estimated_prep_buffer <= 900',
            name=op.f('ck_orders_on_estimated_prep_buffer_between_0_and_900'),
        ),
        sa.CheckConstraint(
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 2700',
            name=op.f('ck_orders_on_estimated_prep_duration_between_0_and_2700'),
        ),
        sa.CheckConstraint(
            '0 <= utilization AND utilization <= 100',
            name=op.f('ck_orders_on_utilization_between_0_and_100'),
        ),
        sa.CheckConstraint(
            '(cancelled_at IS NULL AND cancelled_at_corrected IS NULL) OR (cancelled_at IS NULL AND cancelled_at_corrected IS TRUE) OR (cancelled_at IS NOT NULL AND cancelled_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_1'),
        ),
        sa.CheckConstraint(
            '(courier_accepted_at IS NULL AND courier_accepted_at_corrected IS NULL) OR (courier_accepted_at IS NULL AND courier_accepted_at_corrected IS TRUE) OR (courier_accepted_at IS NOT NULL AND courier_accepted_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_7'),
        ),
        sa.CheckConstraint(
            '(courier_notified_at IS NULL AND courier_notified_at_corrected IS NULL) OR (courier_notified_at IS NULL AND courier_notified_at_corrected IS TRUE) OR (courier_notified_at IS NOT NULL AND courier_notified_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_6'),
        ),
        sa.CheckConstraint(
            '(delivery_at IS NULL AND delivery_at_corrected IS NULL) OR (delivery_at IS NULL AND delivery_at_corrected IS TRUE) OR (delivery_at IS NOT NULL AND delivery_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_10'),
        ),
        sa.CheckConstraint(
            '(dispatch_at IS NULL AND dispatch_at_corrected IS NULL) OR (dispatch_at IS NULL AND dispatch_at_corrected IS TRUE) OR (dispatch_at IS NOT NULL AND dispatch_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_5'),
        ),
        sa.CheckConstraint(
            '(estimated_prep_duration IS NULL AND estimated_prep_duration_corrected IS NULL) OR (estimated_prep_duration IS NULL AND estimated_prep_duration_corrected IS TRUE) OR (estimated_prep_duration IS NOT NULL AND estimated_prep_duration_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_4'),
        ),
        sa.CheckConstraint(
            '(left_pickup_at IS NULL AND left_pickup_at_corrected IS NULL) OR (left_pickup_at IS NULL AND left_pickup_at_corrected IS TRUE) OR (left_pickup_at IS NOT NULL AND left_pickup_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_9'),
        ),
        sa.CheckConstraint(
            '(pickup_at IS NULL AND pickup_at_corrected IS NULL) OR (pickup_at IS NULL AND pickup_at_corrected IS TRUE) OR (pickup_at IS NOT NULL AND pickup_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_8'),
        ),
        sa.CheckConstraint(
            '(restaurant_confirmed_at IS NULL AND restaurant_confirmed_at_corrected IS NULL) OR (restaurant_confirmed_at IS NULL AND restaurant_confirmed_at_corrected IS TRUE) OR (restaurant_confirmed_at IS NOT NULL AND restaurant_confirmed_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_3'),
        ),
        sa.CheckConstraint(
            '(restaurant_notified_at IS NULL AND restaurant_notified_at_corrected IS NULL) OR (restaurant_notified_at IS NULL AND restaurant_notified_at_corrected IS TRUE) OR (restaurant_notified_at IS NOT NULL AND restaurant_notified_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_2'),
        ),
        sa.CheckConstraint(
            '(scheduled_delivery_at IS NULL AND scheduled_delivery_at_corrected IS NULL) OR (scheduled_delivery_at IS NULL AND scheduled_delivery_at_corrected IS TRUE) OR (scheduled_delivery_at IS NOT NULL AND scheduled_delivery_at_corrected IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_corrections_only_for_set_value_0'),
        ),
        sa.CheckConstraint(
            '(ad_hoc IS TRUE AND scheduled_delivery_at IS NULL) OR (ad_hoc IS FALSE AND scheduled_delivery_at IS NOT NULL)',  # noqa:E501
            name=op.f('ck_orders_on_either_ad_hoc_or_scheduled_order'),
        ),
        sa.CheckConstraint(
            'NOT (EXTRACT(EPOCH FROM scheduled_delivery_at - placed_at) < 1800)',
            name=op.f('ck_orders_on_scheduled_orders_not_within_30_minutes'),
        ),
        sa.CheckConstraint(
            'NOT (ad_hoc IS FALSE AND ((EXTRACT(HOUR FROM scheduled_delivery_at) <= 11 AND NOT (EXTRACT(HOUR FROM scheduled_delivery_at) = 11 AND EXTRACT(MINUTE FROM scheduled_delivery_at) = 45)) OR EXTRACT(HOUR FROM scheduled_delivery_at) > 22))',  # noqa:E501
            name=op.f('ck_orders_on_scheduled_orders_within_business_hours'),
        ),
        sa.CheckConstraint(
            'NOT (ad_hoc IS TRUE AND (EXTRACT(HOUR FROM placed_at) < 11 OR EXTRACT(HOUR FROM placed_at) > 22))',  # noqa:E501
            name=op.f('ck_orders_on_ad_hoc_orders_within_business_hours'),
        ),
        sa.CheckConstraint(
            'NOT (cancelled IS FALSE AND cancelled_at IS NOT NULL)',
            name=op.f('ck_orders_on_only_cancelled_orders_may_have_cancelled_at'),
        ),
        sa.CheckConstraint(
            'NOT (cancelled IS TRUE AND delivery_at IS NOT NULL)',
            name=op.f('ck_orders_on_cancelled_orders_must_not_be_delivered'),
        ),
        sa.CheckConstraint(
            'cancelled_at > courier_accepted_at',
            name=op.f('ck_orders_on_ordered_timestamps_16'),
        ),
        sa.CheckConstraint(
            'cancelled_at > courier_notified_at',
            name=op.f('ck_orders_on_ordered_timestamps_15'),
        ),
        sa.CheckConstraint(
            'cancelled_at > delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_21'),
        ),
        sa.CheckConstraint(
            'cancelled_at > dispatch_at',
            name=op.f('ck_orders_on_ordered_timestamps_14'),
        ),
        sa.CheckConstraint(
            'cancelled_at > left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_19'),
        ),
        sa.CheckConstraint(
            'cancelled_at > pickup_at', name=op.f('ck_orders_on_ordered_timestamps_18'),
        ),
        sa.CheckConstraint(
            'cancelled_at > reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_20'),
        ),
        sa.CheckConstraint(
            'cancelled_at > reached_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_17'),
        ),
        sa.CheckConstraint(
            'cancelled_at > restaurant_confirmed_at',
            name=op.f('ck_orders_on_ordered_timestamps_13'),
        ),
        sa.CheckConstraint(
            'cancelled_at > restaurant_notified_at',
            name=op.f('ck_orders_on_ordered_timestamps_12'),
        ),
        sa.CheckConstraint(
            'courier_accepted_at < delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_42'),
        ),
        sa.CheckConstraint(
            'courier_accepted_at < left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_40'),
        ),
        sa.CheckConstraint(
            'courier_accepted_at < pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_39'),
        ),
        sa.CheckConstraint(
            'courier_accepted_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_41'),
        ),
        sa.CheckConstraint(
            'courier_accepted_at < reached_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_38'),
        ),
        sa.CheckConstraint(
            'courier_notified_at < courier_accepted_at',
            name=op.f('ck_orders_on_ordered_timestamps_32'),
        ),
        sa.CheckConstraint(
            'courier_notified_at < delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_37'),
        ),
        sa.CheckConstraint(
            'courier_notified_at < left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_35'),
        ),
        sa.CheckConstraint(
            'courier_notified_at < pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_34'),
        ),
        sa.CheckConstraint(
            'courier_notified_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_36'),
        ),
        sa.CheckConstraint(
            'courier_notified_at < reached_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_33'),
        ),
        sa.CheckConstraint(
            'dispatch_at < courier_accepted_at',
            name=op.f('ck_orders_on_ordered_timestamps_26'),
        ),
        sa.CheckConstraint(
            'dispatch_at < courier_notified_at',
            name=op.f('ck_orders_on_ordered_timestamps_25'),
        ),
        sa.CheckConstraint(
            'dispatch_at < delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_31'),
        ),
        sa.CheckConstraint(
            'dispatch_at < left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_29'),
        ),
        sa.CheckConstraint(
            'dispatch_at < pickup_at', name=op.f('ck_orders_on_ordered_timestamps_28'),
        ),
        sa.CheckConstraint(
            'dispatch_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_30'),
        ),
        sa.CheckConstraint(
            'dispatch_at < reached_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_27'),
        ),
        sa.CheckConstraint(
            'estimated_prep_buffer % 60 = 0',
            name=op.f('ck_orders_on_estimated_prep_buffer_must_be_whole_minutes'),
        ),
        sa.CheckConstraint(
            'estimated_prep_duration % 60 = 0',
            name=op.f('ck_orders_on_estimated_prep_duration_must_be_whole_minutes'),
        ),
        sa.CheckConstraint(
            'left_pickup_at < delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_51'),
        ),
        sa.CheckConstraint(
            'left_pickup_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_50'),
        ),
        sa.CheckConstraint(
            'pickup_at < delivery_at', name=op.f('ck_orders_on_ordered_timestamps_49'),
        ),
        sa.CheckConstraint(
            'pickup_at < left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_47'),
        ),
        sa.CheckConstraint(
            'pickup_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_48'),
        ),
        sa.CheckConstraint(
            'placed_at < cancelled_at', name=op.f('ck_orders_on_ordered_timestamps_2'),
        ),
        sa.CheckConstraint(
            'placed_at < courier_accepted_at',
            name=op.f('ck_orders_on_ordered_timestamps_7'),
        ),
        sa.CheckConstraint(
            'placed_at < courier_notified_at',
            name=op.f('ck_orders_on_ordered_timestamps_6'),
        ),
        sa.CheckConstraint(
            'placed_at < delivery_at', name=op.f('ck_orders_on_ordered_timestamps_11'),
        ),
        sa.CheckConstraint(
            'placed_at < dispatch_at', name=op.f('ck_orders_on_ordered_timestamps_5'),
        ),
        sa.CheckConstraint(
            'placed_at < first_estimated_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_1'),
        ),
        sa.CheckConstraint(
            'placed_at < left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_9'),
        ),
        sa.CheckConstraint(
            'placed_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_10'),
        ),
        sa.CheckConstraint(
            'placed_at < reached_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_8'),
        ),
        sa.CheckConstraint(
            'placed_at < restaurant_confirmed_at',
            name=op.f('ck_orders_on_ordered_timestamps_4'),
        ),
        sa.CheckConstraint(
            'placed_at < restaurant_notified_at',
            name=op.f('ck_orders_on_ordered_timestamps_3'),
        ),
        sa.CheckConstraint(
            'placed_at < scheduled_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_0'),
        ),
        sa.CheckConstraint(
            'reached_delivery_at < delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_52'),
        ),
        sa.CheckConstraint(
            'reached_pickup_at < delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_46'),
        ),
        sa.CheckConstraint(
            'reached_pickup_at < left_pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_44'),
        ),
        sa.CheckConstraint(
            'reached_pickup_at < pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_43'),
        ),
        sa.CheckConstraint(
            'reached_pickup_at < reached_delivery_at',
            name=op.f('ck_orders_on_ordered_timestamps_45'),
        ),
        sa.CheckConstraint(
            'restaurant_confirmed_at < pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_24'),
        ),
        sa.CheckConstraint(
            'restaurant_notified_at < pickup_at',
            name=op.f('ck_orders_on_ordered_timestamps_23'),
        ),
        sa.CheckConstraint(
            'restaurant_notified_at < restaurant_confirmed_at',
            name=op.f('ck_orders_on_ordered_timestamps_22'),
        ),
        sa.CheckConstraint(
            '(pickup_at IS NULL AND pickup_not_confirmed IS NULL) OR (pickup_at IS NOT NULL AND pickup_not_confirmed IS NOT NULL)',  # noqa:E501
            name=op.f('pickup_not_confirmed_only_if_pickup'),
        ),
        sa.CheckConstraint(
            '(delivery_at IS NULL AND delivery_not_confirmed IS NULL) OR (delivery_at IS NOT NULL AND delivery_not_confirmed IS NOT NULL)',  # noqa:E501
            name=op.f('delivery_not_confirmed_only_if_delivery'),
        ),
        sa.CheckConstraint(
            '(delivery_at IS NULL AND courier_waited_at_delivery IS NULL) OR (delivery_at IS NOT NULL AND courier_waited_at_delivery IS NOT NULL)',  # noqa:E501
            name=op.f('courier_waited_at_delivery_only_if_delivery'),
        ),
        sa.ForeignKeyConstraint(
            ['courier_id'],
            [f'{config.CLEAN_SCHEMA}.couriers.id'],
            name=op.f('fk_orders_to_couriers_via_courier_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['customer_id'],
            [f'{config.CLEAN_SCHEMA}.customers.id'],
            name=op.f('fk_orders_to_customers_via_customer_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['delivery_address_id'],
            [f'{config.CLEAN_SCHEMA}.addresses.id'],
            name=op.f('fk_orders_to_addresses_via_delivery_address_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['pickup_address_id'],
            [f'{config.CLEAN_SCHEMA}.addresses.id'],
            name=op.f('fk_orders_to_addresses_via_pickup_address_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['restaurant_id'],
            [f'{config.CLEAN_SCHEMA}.restaurants.id'],
            name=op.f('fk_orders_to_restaurants_via_restaurant_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_orders')),
        *(
            [  # noqa:WPS504
                sa.ForeignKeyConstraint(
                    ['id'],
                    [f'{config.ORIGINAL_SCHEMA}.orders.id'],
                    name=op.f('pk_orders_sanity'),
                    onupdate='RESTRICT',
                    ondelete='RESTRICT',
                ),
                sa.ForeignKeyConstraint(
                    ['delivery_id'],
                    [f'{config.ORIGINAL_SCHEMA}.deliveries.id'],
                    name=op.f('pk_deliveries_sanity'),
                    onupdate='RESTRICT',
                    ondelete='RESTRICT',
                ),
            ]
            if not config.TESTING
            else []
        ),
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_cancelled'),
        'orders',
        ['cancelled'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_cancelled_at_corrected'),
        'orders',
        ['cancelled_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_courier_accepted_at_corrected'),
        'orders',
        ['courier_accepted_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_courier_id'),
        'orders',
        ['courier_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_courier_notified_at_corrected'),
        'orders',
        ['courier_notified_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_customer_id'),
        'orders',
        ['customer_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_delivery_address_id'),
        'orders',
        ['delivery_address_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_delivery_at_corrected'),
        'orders',
        ['delivery_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_delivery_id'),
        'orders',
        ['delivery_id'],
        unique=True,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_dispatch_at_corrected'),
        'orders',
        ['dispatch_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_estimated_prep_buffer'),
        'orders',
        ['estimated_prep_buffer'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_estimated_prep_duration'),
        'orders',
        ['estimated_prep_duration'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_estimated_prep_duration_corrected'),
        'orders',
        ['estimated_prep_duration_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_left_pickup_at_corrected'),
        'orders',
        ['left_pickup_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_pickup_address_id'),
        'orders',
        ['pickup_address_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_pickup_at_corrected'),
        'orders',
        ['pickup_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_placed_at'),
        'orders',
        ['placed_at'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_restaurant_confirmed_at_corrected'),
        'orders',
        ['restaurant_confirmed_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_restaurant_id'),
        'orders',
        ['restaurant_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_restaurant_notified_at_corrected'),
        'orders',
        ['restaurant_notified_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_scheduled_delivery_at'),
        'orders',
        ['scheduled_delivery_at'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_orders_on_scheduled_delivery_at_corrected'),
        'orders',
        ['scheduled_delivery_at_corrected'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision None."""
    op.execute(f'DROP SCHEMA {config.CLEAN_SCHEMA} CASCADE;')
