import uuid
from datetime import datetime

from sqlalchemy import String, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.timezone import DateTimeUTC, utc_now


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    key: Mapped[str] = mapped_column(String, unique=True)
    value: Mapped[str] = mapped_column(JSON, nullable=False)
    is_global: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now)
    modified_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now)
