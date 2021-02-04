"""Remove orders from restaurants with invalid location ...

... and also de-duplicate a couple of redundant addresses.

Revision: #e86290e7305e at 2021-01-23 15:56:59
Revises: #26711cd3f9b9

1) Remove orders

Some restaurants have orders to be picked up at an address that
not their primary address. That is ok if that address is the location
of a second franchise. However, for a small number of restaurants
there is only exactly one order at that other address that often is
located far away from the restaurant's primary location. It looks
like a restaurant signed up with some invalid location that was then
corrected into the primary one.

Use the following SQL statement to obtain a list of these locations
before this migration is run:

SELECT
    orders.pickup_address_id,
    COUNT(*) AS n_orders,
    MIN(placed_at) as first_order_at,
    MAX(placed_at) as last_order_at
FROM
    {config.CLEAN_SCHEMA}.orders
LEFT OUTER JOIN
    {config.CLEAN_SCHEMA}.restaurants
    ON orders.restaurant_id = restaurants.id
WHERE
    orders.pickup_address_id <> restaurants.address_id
GROUP BY
    pickup_address_id;

50 orders with such weird pickup addresses are removed with this migration.


2) De-duplicate addresses

Five restaurants have two pickup addresses that are actually the same location.

The following SQL statement shows them before this migration is run:

SELECT
    orders.restaurant_id,
    restaurants.name,
    restaurants.address_id AS primary_address_id,
    addresses.id AS address_id,
    addresses.street,
    COUNT(*) AS n_orders
FROM
    {config.CLEAN_SCHEMA}.orders
LEFT OUTER JOIN
    {config.CLEAN_SCHEMA}.addresses ON orders.pickup_address_id = addresses.id
LEFT OUTER JOIN
    {config.CLEAN_SCHEMA}.restaurants ON orders.restaurant_id = restaurants.id
WHERE
    orders.restaurant_id IN (
    SELECT
        restaurant_id
    FROM (
        SELECT DISTINCT
            restaurant_id,
            pickup_address_id
        FROM
            {config.CLEAN_SCHEMA}.orders
    ) AS restaurant_locations
    GROUP BY
        restaurant_id
    HAVING
        COUNT(pickup_address_id) > 1
)
GROUP BY
    orders.restaurant_id,
    restaurants.name,
    restaurants.address_id,
    addresses.id,
    addresses.street
ORDER BY
    orders.restaurant_id,
    restaurants.name,
    restaurants.address_id,
    addresses.id,
    addresses.street;


3) Remove addresses without any association

After steps 1) and 2) some addresses are not associated with a restaurant any more.

The following SQL statement lists them before this migration is run:

SELECT
    id,
    street,
    zip_code,
    city
FROM
    {config.CLEAN_SCHEMA}.addresses
WHERE
    id NOT IN (
    SELECT DISTINCT
        pickup_address_id AS id
    FROM
        {config.CLEAN_SCHEMA}.orders
    UNION
    SELECT DISTINCT
        delivery_address_id AS id
    FROM
        {config.CLEAN_SCHEMA}.orders
    UNION
    SELECT DISTINCT
        address_id AS id
    FROM
        {config.CLEAN_SCHEMA}.restaurants
);

4) Ensure every `Restaurant` has exactly one `Address`.

Replace the current `ForeignKeyConstraint` to from `Order` to `Restaurant`
with one that also includes the `Order.pickup_address_id`.
"""

import os

from alembic import op

from urban_meal_delivery import configuration


revision = 'e86290e7305e'
down_revision = '26711cd3f9b9'
branch_labels = None
depends_on = None


config = configuration.make_config('testing' if os.getenv('TESTING') else 'production')


def upgrade():
    """Upgrade to revision e86290e7305e."""
    # 1) Remove orders
    op.execute(
        f"""
        DELETE
        FROM
            {config.CLEAN_SCHEMA}.orders
        WHERE pickup_address_id IN (
            SELECT
                orders.pickup_address_id
            FROM
                {config.CLEAN_SCHEMA}.orders
            LEFT OUTER JOIN
                {config.CLEAN_SCHEMA}.restaurants
                ON orders.restaurant_id = restaurants.id
            WHERE
                orders.pickup_address_id <> restaurants.address_id
            GROUP BY
                orders.pickup_address_id
            HAVING
                COUNT(*) = 1
        );
        """,
    )

    # 2) De-duplicate addresses
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.orders
        SET
            pickup_address_id = 353
        WHERE
            pickup_address_id = 548916;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.orders
        SET
            pickup_address_id = 4850
        WHERE
            pickup_address_id = 6415;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.orders
        SET
            pickup_address_id = 16227
        WHERE
            pickup_address_id = 44627;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.orders
        SET
            pickup_address_id = 44458
        WHERE
            pickup_address_id = 534543;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.orders
        SET
            pickup_address_id = 289997
        WHERE
            pickup_address_id = 309525;
        """,
    )

    # 3) Remove addresses
    op.execute(
        f"""
        DELETE
        FROM
            {config.CLEAN_SCHEMA}.addresses_pixels
        WHERE
            address_id NOT IN (
            SELECT DISTINCT
                pickup_address_id AS id
            FROM
                {config.CLEAN_SCHEMA}.orders
            UNION
            SELECT DISTINCT
                delivery_address_id AS id
            FROM
                {config.CLEAN_SCHEMA}.orders
            UNION
            SELECT DISTINCT
                address_id AS id
            FROM
                {config.CLEAN_SCHEMA}.restaurants
        );
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.addresses
        SET
            primary_id = 302883
        WHERE
            primary_id = 43526;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.addresses
        SET
            primary_id = 47597
        WHERE
            primary_id = 43728;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.addresses
        SET
            primary_id = 159631
        WHERE
            primary_id = 43942;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.addresses
        SET
            primary_id = 275651
        WHERE
            primary_id = 44759;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.addresses
        SET
            primary_id = 156685
        WHERE
            primary_id = 50599;
        """,
    )
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.addresses
        SET
            primary_id = 480206
        WHERE
            primary_id = 51774;
        """,
    )
    op.execute(
        f"""
        DELETE
        FROM
            {config.CLEAN_SCHEMA}.addresses
        WHERE
            id NOT IN (
            SELECT DISTINCT
                pickup_address_id AS id
            FROM
                {config.CLEAN_SCHEMA}.orders
            UNION
            SELECT DISTINCT
                delivery_address_id AS id
            FROM
                {config.CLEAN_SCHEMA}.orders
            UNION
            SELECT DISTINCT
                address_id AS id
            FROM
                {config.CLEAN_SCHEMA}.restaurants
        );
        """,
    )

    # 4) Ensure every `Restaurant` has only one `Order.pickup_address`.
    op.execute(
        f"""
        UPDATE
            {config.CLEAN_SCHEMA}.orders
        SET
            pickup_address_id = 53733
        WHERE
            pickup_address_id = 54892;
        """,
    )
    op.execute(
        f"""
        DELETE
        FROM
            {config.CLEAN_SCHEMA}.addresses
        WHERE
            id = 54892;
        """,
    )
    op.create_unique_constraint(
        'uq_restaurants_on_id_address_id',
        'restaurants',
        ['id', 'address_id'],
        schema=config.CLEAN_SCHEMA,
    )
    op.create_foreign_key(
        op.f('fk_orders_to_restaurants_via_restaurant_id_pickup_address_id'),
        'orders',
        'restaurants',
        ['restaurant_id', 'pickup_address_id'],
        ['id', 'address_id'],
        source_schema=config.CLEAN_SCHEMA,
        referent_schema=config.CLEAN_SCHEMA,
        onupdate='RESTRICT',
        ondelete='RESTRICT',
    )
    op.drop_constraint(
        'fk_orders_to_restaurants_via_restaurant_id',
        'orders',
        type_='foreignkey',
        schema=config.CLEAN_SCHEMA,
    )


def downgrade():
    """Downgrade to revision 26711cd3f9b9."""
    op.create_foreign_key(
        op.f('fk_orders_to_restaurants_via_restaurant_id'),
        'orders',
        'restaurants',
        ['restaurant_id'],
        ['id'],
        source_schema=config.CLEAN_SCHEMA,
        referent_schema=config.CLEAN_SCHEMA,
        onupdate='RESTRICT',
        ondelete='RESTRICT',
    )
    op.drop_constraint(
        'fk_orders_to_restaurants_via_restaurant_id_pickup_address_id',
        'orders',
        type_='foreignkey',
        schema=config.CLEAN_SCHEMA,
    )
    op.drop_constraint(
        'uq_restaurants_on_id_address_id',
        'restaurants',
        type_='unique',
        schema=config.CLEAN_SCHEMA,
    )
