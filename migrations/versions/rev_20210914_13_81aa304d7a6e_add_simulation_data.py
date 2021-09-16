"""Add simulation data.

Revision: # 81aa304d7a6e at 2021-09-14 13:47:03
Revises: # b4dd0b8903a5
"""

import os

import sqlalchemy as sa
from alembic import op

from urban_meal_delivery import configuration


revision = '81aa304d7a6e'
down_revision = 'b4dd0b8903a5'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision 81aa304d7a6e."""
    # Drop unnecessary check constraint.
    op.execute(  # `.delivery_at` is not set for `.cancelled` orders anyways.
        f"""
        ALTER TABLE {config.CLEAN_SCHEMA}.orders
        DROP CONSTRAINT ck_orders_on_ordered_timestamps_21;
        """,
    )  # noqa:WPS355

    # Add forgotten check constraints to the `orders` table.
    op.execute(
        f"""
        ALTER TABLE {config.CLEAN_SCHEMA}.orders
        ADD CONSTRAINT check_orders_on_ordered_timestamps_placed_at_before_pickup_at
        CHECK (placed_at < pickup_at);
        """,
    )  # noqa:WPS355
    op.execute(
        f"""
        ALTER TABLE {config.CLEAN_SCHEMA}.orders
        ADD CONSTRAINT check_orders_on_scheduled_orders_must_be_at_quarters_of_an_hour
        CHECK (
            (
                EXTRACT(MINUTES FROM scheduled_delivery_at)::INTEGER
                % 15 = 0
            )
            AND
            (
                EXTRACT(SECONDS FROM scheduled_delivery_at)::INTEGER
                = 0
            )
        );
        """,
    )  # noqa:WPS355

    # This `UniqueConstraint` is needed by the `replayed_orders` table below.
    op.create_unique_constraint(
        'uq_orders_on_id_ad_hoc',
        'orders',
        ['id', 'ad_hoc'],
        schema=config.CLEAN_SCHEMA,
    )

    op.create_table(
        'replay_simulations',
        sa.Column('id', sa.Integer, autoincrement=True),
        sa.Column('city_id', sa.SmallInteger, nullable=False),
        sa.Column('strategy', sa.Unicode(length=100), nullable=False),
        sa.Column('run', sa.SmallInteger, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_replay_simulations')),
        sa.ForeignKeyConstraint(
            ['city_id'],
            [f'{config.CLEAN_SCHEMA}.cities.id'],
            name=op.f('fk_replay_simulations_to_cities_via_city_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.UniqueConstraint(
            'city_id',
            'strategy',
            'run',
            name=op.f('uq_replay_simulations_on_city_id_strategy_run'),
        ),
        sa.CheckConstraint('run >= 0', name=op.f('run_is_a_count')),
        schema=config.CLEAN_SCHEMA,
    )

    op.create_table(
        'replayed_orders',
        sa.Column('simulation_id', sa.Integer, primary_key=True),
        sa.Column('actual_order_id', sa.Integer, primary_key=True),
        sa.Column('ad_hoc', sa.Boolean, nullable=False),
        sa.Column('placed_at', sa.DateTime, nullable=False),
        sa.Column('scheduled_delivery_at', sa.DateTime),
        sa.Column('cancelled_at', sa.DateTime),
        sa.Column('estimated_prep_duration', sa.SmallInteger),
        sa.Column('restaurant_notified_at', sa.DateTime),
        sa.Column('restaurant_confirmed_at', sa.DateTime),
        sa.Column('restaurant_ready_at', sa.DateTime),
        sa.Column('dispatch_at', sa.DateTime),
        sa.Column('first_estimated_delivery_at', sa.DateTime),
        sa.Column('courier_id', sa.Integer),
        sa.Column('courier_notified_at', sa.DateTime),
        sa.Column('courier_accepted_at', sa.DateTime),
        sa.Column('utilization', sa.SmallInteger),
        sa.Column('reached_pickup_at', sa.DateTime),
        sa.Column('pickup_at', sa.DateTime),
        sa.Column('left_pickup_at', sa.DateTime),
        sa.Column('reached_delivery_at', sa.DateTime),
        sa.Column('delivery_at', sa.DateTime),
        sa.PrimaryKeyConstraint(
            'simulation_id', 'actual_order_id', name=op.f('pk_replayed_orders'),
        ),
        sa.ForeignKeyConstraint(
            ['simulation_id'],
            [f'{config.CLEAN_SCHEMA}.replay_simulations.id'],
            name=op.f('fk_replayed_orders_to_replay_simulations_via_simulation_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            # Needs the `UniqueConstraint` from above.
            ['actual_order_id', 'ad_hoc'],
            [
                f'{config.CLEAN_SCHEMA}.orders.id',
                f'{config.CLEAN_SCHEMA}.orders.ad_hoc',
            ],
            name=op.f('fk_replayed_orders_to_orders_via_actual_order_id_ad_hoc'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['courier_id'],
            [f'{config.CLEAN_SCHEMA}.couriers.id'],
            name=op.f('fk_replayed_orders_to_couriers_via_courier_id'),
            onupdate='RESTRICT',
            ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            """
            (
                ad_hoc IS TRUE
                AND
                scheduled_delivery_at IS NULL
            )
            OR
            (
                ad_hoc IS FALSE
                AND
                scheduled_delivery_at IS NOT NULL
            )
            """,
            name=op.f('either_ad_hoc_or_scheduled_order'),
        ),
        sa.CheckConstraint(
            """
            NOT (
                ad_hoc IS TRUE
                AND (
                    EXTRACT(HOUR FROM placed_at) < 11
                    OR
                    EXTRACT(HOUR FROM placed_at) > 22
                )
            )
            """,
            name=op.f('ad_hoc_orders_within_business_hours'),
        ),
        sa.CheckConstraint(
            """
            NOT (
                ad_hoc IS FALSE
                AND (
                    (
                        EXTRACT(HOUR FROM scheduled_delivery_at) <= 11
                        AND
                        NOT (
                            EXTRACT(HOUR FROM scheduled_delivery_at) = 11
                            AND
                            EXTRACT(MINUTE FROM scheduled_delivery_at) = 45
                        )
                    )
                    OR
                    EXTRACT(HOUR FROM scheduled_delivery_at) > 22
                )
            )
            """,
            name=op.f('scheduled_orders_within_business_hours'),
        ),
        sa.CheckConstraint(
            """
            (
                EXTRACT(MINUTES FROM scheduled_delivery_at)::INTEGER
                % 15 = 0
            )
            AND
            (
                EXTRACT(SECONDS FROM scheduled_delivery_at)::INTEGER
                = 0
            )
            """,
            name=op.f('scheduled_orders_must_be_at_quarters_of_an_hour'),
        ),
        sa.CheckConstraint(
            """
            NOT (
                EXTRACT(EPOCH FROM scheduled_delivery_at - placed_at) < 1800
            )
            """,
            name=op.f('scheduled_orders_not_within_30_minutes'),
        ),
        sa.CheckConstraint(
            """
            cancelled_at IS NOT NULL
            OR
            (
                restaurant_notified_at IS NOT NULL
                AND
                restaurant_confirmed_at IS NOT NULL
                AND
                restaurant_ready_at IS NOT NULL
                AND
                dispatch_at IS NOT NULL
                AND
                courier_id IS NOT NULL
                AND
                courier_notified_at IS NOT NULL
                AND
                courier_accepted_at IS NOT NULL
                AND
                reached_pickup_at IS NOT NULL
                AND
                pickup_at IS NOT NULL
                AND
                left_pickup_at IS NOT NULL
                AND
                reached_delivery_at IS NOT NULL
                AND
                delivery_at IS NOT NULL
            )
            """,
            name=op.f('orders_must_be_either_cancelled_or_fully_simulated'),
        ),
        sa.CheckConstraint(
            """
            NOT (  -- Only occurred in 528 of 660,608 orders in the actual data.
                cancelled_at IS NOT NULL
                AND
                pickup_at IS NOT NULL
            )
            AND
            NOT (  -- Only occurred in 176 of 660,608 orders in the actual data.
                cancelled_at IS NOT NULL
                AND
                left_pickup_at IS NOT NULL
            )
            AND
            NOT (  -- Never occurred in the actual data.
                cancelled_at IS NOT NULL
                AND
                reached_delivery_at IS NOT NULL
            )
            AND
            NOT (  -- Never occurred in the actual data.
                cancelled_at IS NOT NULL
                AND
                delivery_at IS NOT NULL
            )
            """,
            name=op.f('cancellations_may_only_occur_before_pickup'),
        ),
        sa.CheckConstraint(
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 3600',
            name=op.f('estimated_prep_duration_between_0_and_3600'),
        ),
        sa.CheckConstraint(
            'estimated_prep_duration % 60 = 0',
            name=op.f('estimated_prep_duration_must_be_whole_minutes'),
        ),
        sa.CheckConstraint(
            '0 <= utilization AND utilization <= 100',
            name=op.f('utilization_between_0_and_100'),
        ),
        sa.CheckConstraint(
            """
            NOT (
                EXTRACT(HOUR FROM restaurant_notified_at) < 11
                OR
                EXTRACT(HOUR FROM dispatch_at) < 11
            )
            """,
            name=op.f('orders_dispatched_in_business_hours'),
        ),
        *(
            sa.CheckConstraint(
                constraint, name='ordered_timestamps_{index}'.format(index=index),
            )
            for index, constraint in enumerate(
                (
                    'placed_at < scheduled_delivery_at',
                    'placed_at < cancelled_at',
                    'placed_at < restaurant_notified_at',
                    'placed_at < restaurant_confirmed_at',
                    'placed_at < restaurant_ready_at',
                    'placed_at < dispatch_at',
                    'placed_at < first_estimated_delivery_at',
                    'placed_at < courier_notified_at',
                    'placed_at < courier_accepted_at',
                    'placed_at < reached_pickup_at',
                    'placed_at < pickup_at',
                    'placed_at < left_pickup_at',
                    'placed_at < reached_delivery_at',
                    'placed_at < delivery_at',
                    'cancelled_at > restaurant_notified_at',
                    'cancelled_at > restaurant_confirmed_at',
                    'cancelled_at > restaurant_ready_at',
                    'cancelled_at > dispatch_at',
                    'cancelled_at > courier_notified_at',
                    'cancelled_at > courier_accepted_at',
                    'cancelled_at > reached_pickup_at',
                    'restaurant_notified_at < restaurant_confirmed_at',
                    'restaurant_notified_at < restaurant_ready_at',
                    'restaurant_notified_at < pickup_at',
                    'restaurant_confirmed_at < restaurant_ready_at',
                    'restaurant_confirmed_at < pickup_at',
                    'restaurant_ready_at < pickup_at',
                    'dispatch_at < first_estimated_delivery_at',
                    'dispatch_at < courier_notified_at',
                    'dispatch_at < courier_accepted_at',
                    'dispatch_at < reached_pickup_at',
                    'dispatch_at < pickup_at',
                    'dispatch_at < left_pickup_at',
                    'dispatch_at < reached_delivery_at',
                    'dispatch_at < delivery_at',
                    'courier_notified_at < courier_accepted_at',
                    'courier_notified_at < reached_pickup_at',
                    'courier_notified_at < pickup_at',
                    'courier_notified_at < left_pickup_at',
                    'courier_notified_at < reached_delivery_at',
                    'courier_notified_at < delivery_at',
                    'courier_accepted_at < reached_pickup_at',
                    'courier_accepted_at < pickup_at',
                    'courier_accepted_at < left_pickup_at',
                    'courier_accepted_at < reached_delivery_at',
                    'courier_accepted_at < delivery_at',
                    'reached_pickup_at < pickup_at',
                    'reached_pickup_at < left_pickup_at',
                    'reached_pickup_at < reached_delivery_at',
                    'reached_pickup_at < delivery_at',
                    'pickup_at < left_pickup_at',
                    'pickup_at < reached_delivery_at',
                    'pickup_at < delivery_at',
                    'left_pickup_at < reached_delivery_at',
                    'left_pickup_at < delivery_at',
                    'reached_delivery_at < delivery_at',
                ),
            )
        ),
        schema=config.CLEAN_SCHEMA,
    )

    op.create_index(
        op.f('ix_replay_simulations_on_city_id'),
        'replay_simulations',
        ['city_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_replay_simulations_on_strategy'),
        'replay_simulations',
        ['strategy'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )
    op.create_index(
        op.f('ix_replayed_orders_on_courier_id'),
        'replayed_orders',
        ['courier_id'],
        unique=False,
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision b4dd0b8903a5."""
    op.drop_table('replayed_orders', schema=config.CLEAN_SCHEMA)
    op.drop_table('replay_simulations', schema=config.CLEAN_SCHEMA)
    op.drop_constraint(
        'uq_orders_on_id_ad_hoc', 'orders', type_=None, schema=config.CLEAN_SCHEMA,
    )
    op.execute(
        f"""
        ALTER TABLE {config.CLEAN_SCHEMA}.orders
        DROP CONSTRAINT check_orders_on_scheduled_orders_must_be_at_quarters_of_an_hour;
        """,
    )  # noqa:WPS355
    op.execute(
        f"""
        ALTER TABLE {config.CLEAN_SCHEMA}.orders
        DROP CONSTRAINT check_orders_on_ordered_timestamps_placed_at_before_pickup_at;
        """,
    )  # noqa:WPS355
    op.execute(
        f"""
        ALTER TABLE {config.CLEAN_SCHEMA}.orders
        ADD CONSTRAINT ck_orders_on_ordered_timestamps_21
        CHECK (cancelled_at > delivery_at);
        """,
    )  # noqa:WPS355
