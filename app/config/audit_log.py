import logging
from typing import Annotated
from opentelemetry import trace
from opentelemetry.trace import SpanContext
from deepdiff import DeepDiff
from app.config.auth import Authenticator, AuthenticatorDep, get_current_user
from fastapi import Request, Depends
from app.config.auth import TokenOptionalDep
from app.config.database import Base, DbDep
from app.features.audit_log.models import ActorType, AuditLog

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AuditLogger:
    def __init__(self, token: str | None, request: Request, authenticator: Authenticator, db: DbDep):
        self.token = token
        self.request = request
        self.authenticator = authenticator
        self.db = db

    async def log(
        self,
        action: str,
        *,
        old_resource: Base | None = None,
        new_resource: Base | None = None,
        exclude_columns: list[str] | None = None,
        track_current_user: bool = True,
    ) -> None:
        with tracer.start_as_current_span("audit-logging") as span:
            audit_log = AuditLog()
            audit_log.action = action

            # Actor data
            if track_current_user and self.token:
                auth_user = get_current_user(self.token, self.authenticator)
                audit_log.actor_type = ActorType.USER
                audit_log.actor_id = auth_user.id

            # Trace data
            ctx: SpanContext = span.get_span_context()
            audit_log.trace_id = "{:032x}".format(ctx.trace_id)
            if track_current_user:
                audit_log.request_ip_address = self.request.client.host if self.request.client else None
                audit_log.request_user_agent = self.request.headers["User-Agent"]
                audit_log.request_method = self.request.method
                audit_log.request_url = str(self.request.url)

            # Resource data
            if old_resource is not None:
                audit_log.old_value = old_resource.to_dict(nested=True, exclude=exclude_columns)
                audit_log.resource_type = old_resource.__tablename__
                audit_log.resource_id = old_resource.id
            if new_resource is not None:
                audit_log.new_value = new_resource.to_dict(nested=True, exclude=exclude_columns)
            if new_resource is not None and old_resource is not None:
                audit_log.changed_value = DeepDiff(
                    old_resource.to_dict(nested=True, exclude=exclude_columns),
                    new_resource.to_dict(nested=True, exclude=exclude_columns),
                )

            self.db.add(audit_log)
            await self.db.commit()


def get_audit_logger(
    token: TokenOptionalDep,
    request: Request,
    authenticator: AuthenticatorDep,
    db: DbDep,
):
    return AuditLogger(token, request, authenticator, db)


AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger)]
