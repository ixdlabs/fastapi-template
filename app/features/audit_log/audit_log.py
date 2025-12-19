from sqlalchemy.orm import Session
from app.features.audit_log.models import AuditLog, ActorType
from typing import Any
import uuid


def create_audit_log(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    actor_type: ActorType,
    action: str,
    resource_type: str,
    resource: str,
    resource_id: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    changed_value: dict[str, Any] | None = None,
    request_meta: dict | None = None,
):
    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource=resource,
        resource_id=resource_id,
        old_value=old_value,
        new_value=new_value,
        changed_value=changed_value,
        request_id=request_meta.get("request_id") if request_meta else None,
        request_ip_address=request_meta.get("ip"),
        request_user_agent=request_meta.get("user_agent"),
        request_method=request_meta.get("method"),
        request_endpoint=request_meta.get("endpoint"),
    )

    db.add(log)
    db.commit()
