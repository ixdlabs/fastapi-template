"""
This module defines the AuditLogger class responsible for tracking and recording audit logs
for resource changes within the application. It captures actor information, request metadata,
resource identity, and snapshots of the resource before and after changes.
"""

import logging
from typing import Annotated, Literal
from opentelemetry import trace
from opentelemetry.trace import SpanContext
from deepdiff import DeepDiff
import orjson
from app.config.auth import AuthException, Authenticator, AuthenticatorDep
from fastapi import Request, Depends
from app.config.database import Base, DbDep
from app.features.audit_log.models.audit_log import ActorType, AuditLog

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# Update this list to exclude any additional columns from audit logging.
default_exclude_columns = ["hashed_password", "hashed_token"]


class AuditLogger:
    tracked_value: dict | None = None

    def __init__(self, request: Request | None, authenticator: Authenticator, db: DbDep):
        self.request = request
        self.authenticator = authenticator
        self.db = db

    async def track(self, resource: Base):
        """
        Track the current state of the resource before any changes are made.
        This should be called before modifying the resource to capture its original state.

        This is ignored for `create` and `delete` actions.
        """
        self.tracked_value = resource.to_dict(nested=True, exclude=default_exclude_columns)

    async def record(self, action: Literal["create", "delete"] | str, resource: Base) -> None:
        """
        Record an audit log entry for the specified action and resource.
        The actual database commit is not handled here; it should be done by the caller.

        For `delete` actions, call this before deleting the resource from the database.
        For other actions, call this making the change but before committing the transaction.
        """
        with tracer.start_as_current_span("audit-logging") as span:
            audit_log = AuditLog()
            audit_log.action = action

            # Actor
            # ----------------------------------------------------------------------------------------------------------
            audit_log.actor_type = ActorType.ANONYMOUS
            if (
                self.request is not None
                and "Authorization" in self.request.headers
                and self.request.headers["Authorization"].startswith("Bearer ")
            ):
                token = self.request.headers["Authorization"].split(" ")[1]
                try:
                    user = self.authenticator.user(token)
                    audit_log.actor_type = ActorType.USER
                    audit_log.actor_id = user.id
                except AuthException:
                    pass

            # Trace / request metadata
            # ----------------------------------------------------------------------------------------------------------
            ctx: SpanContext = span.get_span_context()
            audit_log.trace_id = f"{ctx.trace_id:032x}"

            if self.request is not None:
                audit_log.request_ip_address = self.request.client.host if self.request.client else None
                audit_log.request_user_agent = self.request.headers.get("User-Agent")
                audit_log.request_method = self.request.method
                audit_log.request_url = str(self.request.url)

            # Resource identity
            # ----------------------------------------------------------------------------------------------------------
            if resource.id is None:
                raise ValueError(
                    "Resource must have an ID to be logged in audit log, "
                    "either commit the resource first or manually set the ID."
                )
            if resource is not None:
                audit_log.resource_type = resource.__tablename__
                audit_log.resource_id = resource.id

            # Resource snapshots
            # ----------------------------------------------------------------------------------------------------------
            audit_log.new_value = resource.to_dict(nested=True, exclude=default_exclude_columns)
            if action == "delete":
                audit_log.old_value = audit_log.new_value
                audit_log.new_value = None
            elif action == "create":
                pass
            elif self.tracked_value is not None:
                audit_log.old_value = self.tracked_value
                changed_value = DeepDiff(audit_log.old_value, audit_log.new_value)
                audit_log.changed_value = orjson.loads(orjson.dumps(changed_value))

            # Persist audit log (Do not commit here, commit should be handled by caller)
            # ----------------------------------------------------------------------------------------------------------
            self.db.add(audit_log)


def get_audit_logger(request: Request, authenticator: AuthenticatorDep, db: DbDep):
    return AuditLogger(request, authenticator, db)


AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger)]
