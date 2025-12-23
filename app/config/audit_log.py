import logging
from typing import Annotated
import uuid
from opentelemetry import trace
from opentelemetry.trace import SpanContext
from deepdiff import DeepDiff
from app.config.auth import Authenticator, AuthenticatorDep, get_current_user
from fastapi import Request, Depends
from app.config.auth import TokenOptionalDep
from app.config.database import Base

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AuditLogger:
    data: dict[str, dict | uuid.UUID | str | None] = {}

    def __init__(self, token: str | None, request: Request, authenticator: Authenticator):
        self.token = token
        self.request = request
        self.authenticator = authenticator

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
            self.data["action"] = action

            # Actor data
            self.data["actor_type"] = "anonymous" if track_current_user else "system"
            if track_current_user and self.token:
                auth_user = get_current_user(self.token, self.authenticator)
                self.data["actor_type"] = "user"
                self.data["actor_id"] = auth_user.id

            # Trace data
            ctx: SpanContext = span.get_span_context()
            self.data["trace_id"] = "{:032x}".format(ctx.trace_id)
            if track_current_user:
                self.data["request_ip_address"] = self.request.client.host if self.request.client else None
                self.data["request_user_agent"] = self.request.headers["User-Agent"]
                self.data["request_method"] = self.request.method
                self.data["request_url"] = str(self.request.url)

            # Resource data
            if old_resource is not None:
                self.data["old_values"] = old_resource.to_dict(nested=True, exclude=exclude_columns)
                resource = old_resource
            if new_resource is not None:
                self.data["new_values"] = new_resource.to_dict(nested=True, exclude=exclude_columns)
                resource = new_resource
            if new_resource is not None and old_resource is not None:
                self.data["changed_values"] = DeepDiff(
                    self.data["old_values"], self.data["new_values"], ignore_order=True
                ).to_dict()
            if resource is not None:
                self.data["resource_type"] = resource.__tablename__
                self.data["resource_id"] = resource.id

            logger.info("Audit Log: %s", self.data)


def get_audit_logger(token: TokenOptionalDep, request: Request, authenticator: AuthenticatorDep):
    return AuditLogger(token, request, authenticator)


AuditLoggerDep = Annotated[AuditLogger, Depends(get_audit_logger)]
