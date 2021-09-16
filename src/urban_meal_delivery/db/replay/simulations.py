"""Provide the ORM's `ReplaySimulation` model for the replay simulations."""


import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery.db import meta


class ReplaySimulation(meta.Base):
    """A simulation of the UDP's routing given a strategy ...

    ... for the orders as they arrived in reality.
    """

    __tablename__ = 'replay_simulations'

    # Columns
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)  # noqa:WPS125
    city_id = sa.Column(sa.SmallInteger, nullable=False, index=True)
    strategy = sa.Column(sa.Unicode(length=100), nullable=False, index=True)
    # `.run` may be used as random seed.
    run = sa.Column(sa.SmallInteger, nullable=False)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['city_id'], ['cities.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        # A `.strategy` can be replayed several times per `.city`.
        sa.UniqueConstraint('city_id', 'strategy', 'run'),
        sa.CheckConstraint('run >= 0', name='run_is_a_count'),
    )

    # Relationships
    city = orm.relationship('City', back_populates='replays')
    orders = orm.relationship('ReplayedOrder', back_populates='simulation')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({strategy} #{run} in {city})>'.format(
            cls=self.__class__.__name__,
            strategy=self.strategy,
            run=self.run,
            city=self.city.name,
        )
