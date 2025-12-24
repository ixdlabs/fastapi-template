import logging
from typing import Annotated
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


class AuditLogger:
    def __init__(self, token: str | None, request: Request, authenticator: Authenticator, db: DbDep):
        self.token = token
        self.request = request
        self.authenticator = authenticator
        self.db = db

    async def create_log(
        self,
        action: str,
        *,
        old_resource: Base | None = None,
        new_resource: Base | None = None,
        exclude_columns: list[str] | None = None,
        track_current_user: bool = True,
        commit: bool = False,
    ) -> None:
        assert old_resource is not None or new_resource is not None, (
            "Either old_resource or new_resource must be provided"
        )

        with tracer.start_as_current_span("audit-logging") as span:
            try:
                audit_log = AuditLog()
                self._populate_audit_log_from_context(
                    audit_log, span, action, old_resource, new_resource, exclude_columns, track_current_user
                )
                self.db.add(audit_log)
                if commit:
                    await self.db.commit()
            except Exception:
                logger.error("Failed to log audit event", exc_info=True)

    def _populate_audit_log_from_context(
        self,
        audit_log: AuditLog,
        span: trace.Span,
        action: str,
        old_resource: Base | None,
        new_resource: Base | None,
        exclude_columns: list[str] | None,
        track_current_user: bool,
    ):
        audit_log.action = action

        # Actor data
        audit_log.actor_type = ActorType.ANONYMOUS
        if track_current_user and self.token:
            try:
                auth_user = self.authenticator.user(self.token)
                audit_log.actor_type = ActorType.USER
                audit_log.actor_id = auth_user.id
            except AuthException:
                pass

        # Trace data
        ctx: SpanContext = span.get_span_context()
        audit_log.trace_id = "{:032x}".format(ctx.trace_id)
        if track_current_user:
            audit_log.request_ip_address = self.request.client.host if self.request.client else None
            audit_log.request_user_agent = self.request.headers["User-Agent"]
            audit_log.request_method = self.request.method
            audit_log.request_url = str(self.request.url)

        # Resource data
        resource: Base | None = None
        if old_resource is not None:
            audit_log.old_value = old_resource.to_dict(nested=True, exclude=exclude_columns)
            audit_log.resource_type = old_resource.__tablename__
            audit_log.resource_id = old_resource.id
            resource = old_resource
        if new_resource is not None:
            audit_log.new_value = new_resource.to_dict(nested=True, exclude=exclude_columns)
            resource = resource or new_resource
        if new_resource is not None and old_resource is not None:
            audit_log.changed_value = DeepDiff(
                old_resource.to_dict(nested=True, exclude=exclude_columns),
                new_resource.to_dict(nested=True, exclude=exclude_columns),
            )

        if resource is not None:
            audit_log.resource_type = resource.__tablename__
            audit_log.resource_id = resource.id


def get_audit_logger(
    token: TokenOptionalDep,
    request: Request,
    authenticator: AuthenticatorDep,
    db: DbDep,
):
    return AuditLogger(token, request, authenticator, db)


AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger)]
