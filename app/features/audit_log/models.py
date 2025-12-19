import enum

from typing import Any
from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

import uuid
from app.db.base import Base


class ActorType(enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    actor_type: Mapped[str] = Column(enum.Enum("USER"), nullable=False)
    action: Mapped[str] = Column(String, nullable=False)
    resource_type: Mapped[str] = Column(String, nullable=False)
    resource: Mapped[str] = Column(String, nullable=False)
    resource_id: Mapped[str] = Column(String, nullable=True)
    old_value: Mapped[dict[str, Any]] = Column(JSON, nullable=True)
    new_value: Mapped[dict[str, Any]] = Column(JSON, nullable=True)
    changed_value: Mapped[dict[str, Any]] = Column(JSON, nullable=True)
    request_id: Mapped[str] = Column(String, nullable=True)
    request_ip_address: Mapped[str] = Column(String, nullable=True)
    request_user_agent: Mapped[str] = Column(String, nullable=True)
    request_method: Mapped[str] = Column(String, nullable=True)
    request_endpoint: Mapped[str] = Column(String, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    modified_at: Mapped[datetime] = Column(DateTime(timezone=True), onupdate=func.now())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
