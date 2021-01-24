"""Provide the ORM's `Restaurant` model."""

import sqlalchemy as sa
from sqlalchemy import orm

from urban_meal_delivery.db import meta


class Restaurant(meta.Base):
    """A restaurant selling meals on the UDP.

    In the historic dataset, a `Restaurant` may have changed its `Address`
    throughout its life time. The ORM model only stores the current one,
    which in most cases is also the only one.
    """

    __tablename__ = 'restaurants'

    # Columns
    id = sa.Column(  # noqa:WPS125
        sa.SmallInteger, primary_key=True, autoincrement=False,
    )
    created_at = sa.Column(sa.DateTime, nullable=False)
    name = sa.Column(sa.Unicode(length=45), nullable=False)
    address_id = sa.Column(sa.Integer, nullable=False, index=True)
    estimated_prep_duration = sa.Column(sa.SmallInteger, nullable=False)

    # Constraints
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['address_id'], ['addresses.id'], onupdate='RESTRICT', ondelete='RESTRICT',
        ),
        sa.CheckConstraint(
            '0 <= estimated_prep_duration AND estimated_prep_duration <= 2400',
            name='realistic_estimated_prep_duration',
        ),
    )

    # Relationships
    address = orm.relationship('Address', back_populates='restaurant')
    orders = orm.relationship('Order', back_populates='restaurant')

    def __repr__(self) -> str:
        """Non-literal text representation."""
        return '<{cls}({name})>'.format(cls=self.__class__.__name__, name=self.name)
