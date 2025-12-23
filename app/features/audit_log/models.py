import enum
import uuid
from datetime import datetime
from typing import Any


from sqlalchemy import String, DateTime, JSON, ForeignKey, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum


from app.config.database import Base


class ActorType(enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ANONYMOUS = "ANONYMOUS"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    actor_type: Mapped[str] = mapped_column(Enum(ActorType))
    action: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str] = mapped_column(String)
    resource: Mapped[str] = mapped_column(String)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID)

    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    changed_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    trace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    request_ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    request_user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    request_method: Mapped[str | None] = mapped_column(String, nullable=True)
    request_url: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
