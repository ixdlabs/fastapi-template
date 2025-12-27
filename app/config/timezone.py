import datetime
from typing import override

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


def utc_now():
    """Get the current UTC time."""
    return datetime.datetime.now(datetime.timezone.utc)


# Timezone Aware DateTime TypeDecorator
# Ensure UTC is stored in the database and that TZ aware dates are returned for all dialects.
# Taken from: https://github.com/litestar-org/advanced-alchemy/blob/main/advanced_alchemy/types/datetime.py
# ----------------------------------------------------------------------------------------------------------------------


class DateTimeUTC(TypeDecorator[datetime.datetime]):
    """Timezone Aware DateTime"""

    impl = DateTime(timezone=True)
    cache_ok = True

    @property
    @override
    def python_type(self) -> type[datetime.datetime]:
        return datetime.datetime

    @override
    def process_bind_param(self, value: datetime.datetime | None, dialect: Dialect) -> datetime.datetime | None:
        if value is None:
            return value
        if not value.tzinfo:
            raise TypeError("tzinfo is required")
        return value.astimezone(datetime.timezone.utc)

    @override
    def process_result_value(self, value: datetime.datetime | None, dialect: Dialect) -> datetime.datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value
