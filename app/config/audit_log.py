import logging
from typing import Annotated, Literal
from opentelemetry import trace
from opentelemetry.trace import SpanContext
from deepdiff import DeepDiff
from app.config.auth import AuthException, Authenticator, AuthenticatorDep
from fastapi import Request, Depends
from app.config.auth import TokenOptionalDep
from app.config.database import Base, DbDep
from app.features.audit_log.models import ActorType, AuditLog

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


default_exclude_columns = ["hashed_password"]


class AuditLogger:
    def __init__(self, token: str | None, request: Request, authenticator: Authenticator, db: DbDep):
        self.token = token
        self.request = request
        self.authenticator = authenticator
        self.db = db

    async def add(
        self,
        action: Literal["create", "delete", "update"],
        resource: Base,
        *,
        exclude_columns: list[str] | None = None,
        track_current_user: bool = True,
    ) -> None:
        exclude_columns = [*default_exclude_columns, *(exclude_columns or [])]
        with tracer.start_as_current_span("audit-logging") as span:
            audit_log = AuditLog()
            audit_log.action = action

            # Actor
            # ----------------------------------------------------------------------------------------------------------
            audit_log.actor_type = ActorType.ANONYMOUS
            if track_current_user and self.token:
                try:
                    user = self.authenticator.user(self.token)
                    audit_log.actor_type = ActorType.USER
                    audit_log.actor_id = user.id
                except AuthException:
                    pass

            # Trace / request metadata
            # ----------------------------------------------------------------------------------------------------------
            ctx: SpanContext = span.get_span_context()
            audit_log.trace_id = f"{ctx.trace_id:032x}"

            if track_current_user:
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
            if action == "delete":
                audit_log.old_value = resource.to_dict(nested=True, exclude=exclude_columns)
            elif action == "create":
                audit_log.new_value = resource.to_dict(nested=True, exclude=exclude_columns)
            else:
                audit_log.new_value = resource.to_dict(nested=True, exclude=exclude_columns)
                old_resource = await self.db.get(type(resource), resource.id)
                if old_resource is not None:
                    audit_log.old_value = old_resource.to_dict(nested=True, exclude=exclude_columns)
                    audit_log.changed_value = DeepDiff(audit_log.old_value, audit_log.new_value)

            # Persist audit log (Do not commit here, commit should be handled by caller)
            # ----------------------------------------------------------------------------------------------------------
            self.db.add(audit_log)


def get_audit_logger(
    token: TokenOptionalDep,
    request: Request,
    authenticator: AuthenticatorDep,
    db: DbDep,
):
    return AuditLogger(token, request, authenticator, db)


AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger)]
