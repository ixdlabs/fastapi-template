"""
This module provides pagination utilities for database queries.
"""

from collections.abc import Callable
from pydantic import BaseModel
from sqlalchemy import Select, func, select

from app.config.database import DbDep


# A generic paginated response model
# ----------------------------------------------------------------------------------------------------------------------


class Page[DataT](BaseModel):
    """A paginated response model."""

    count: int
    items: list[DataT]

    def map_to[DataU](self, function: Callable[[DataT], DataU]) -> "Page[DataU]":
        """Maps the items of the page to another type using the provided function."""
        return Page(
            count=self.count,
            items=[function(item) for item in self.items],
        )


# Pagination utility function
# ----------------------------------------------------------------------------------------------------------------------


async def paginate[DataT](db: DbDep, stmt: Select[tuple[DataT]], limit: int = 100, offset: int = 0) -> Page[DataT]:
    """Paginates the given SQLAlchemy Select statement."""
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()
    data_result = await db.execute(stmt.limit(limit).offset(offset))
    data = list(data_result.scalars().all())
    return Page(count=total, items=data)
