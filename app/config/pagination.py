"""
This module provides pagination utilities for database queries.
"""

from typing import Callable, Tuple
from pydantic import BaseModel
from sqlalchemy import Select, func

from app.config.database import DbDep


# A generic paginated response model
# ----------------------------------------------------------------------------------------------------------------------


class Page[DataT](BaseModel):
    """A paginated response model."""

    count: int
    items: list[DataT]

    def map_to[DataU](self, func: Callable[[DataT], DataU]) -> "Page[DataU]":
        """Maps the items of the page to another type using the provided function."""
        return Page[DataU](
            count=self.count,
            items=[func(item) for item in self.items],
        )


# Pagination utility function
# ----------------------------------------------------------------------------------------------------------------------


async def paginate[DataT](db: DbDep, items: Select[Tuple[DataT]]) -> Page[DataT]:
    """Paginates the given SQLAlchemy Select statement."""
    total = await db.execute(items.with_only_columns([func.count()])).scalar_one()
    results = await db.execute(items).scalars().all()
    return Page[DataT](count=total, items=results)
