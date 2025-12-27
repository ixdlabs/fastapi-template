import uuid
from fastapi import Request
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.auth import Authenticator
from starlette.types import Scope
from starlette.datastructures import Headers

from app.config.audit_log import AuditLogger
from app.features.audit_logs.models.audit_log import ActorType, AuditLog

from app.features.users.models.user import User
from app.fixtures.user_factory import UserFactory


def make_request_with_token(token: str | None) -> Request:
    headers = {"User-Agent": "pytest-agent"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/some/path",
        "headers": Headers(headers).raw,
        "query_string": b"x=1",
        "client": ("203.0.113.10", 12345),
    }
    return Request(scope)


@pytest.fixture
def request_fixture() -> Request:
    return make_request_with_token(None)


async def fetch_single_audit_log(db_fixture: AsyncSession) -> AuditLog:
    result = await db_fixture.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))
    audit = result.scalars().first()
    assert audit is not None
    return audit


# Tests for AuditLogger
# ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_logger_raises_value_error_when_resource_missing_id(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator, request_fixture: Request
):
    logger = AuditLogger(request=request_fixture, authenticator=authenticator_fixture, db=db_fixture)
    resource: User = UserFactory.build(id=None)

    with pytest.raises(ValueError, match="Resource must have an ID to be logged in audit log"):
        await logger.record("create", resource)


@pytest.mark.asyncio
async def test_audit_logger_create_records_anonymous_actor_and_request_metadata(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator, request_fixture: Request
):
    logger = AuditLogger(request=request_fixture, authenticator=authenticator_fixture, db=db_fixture)
    resource: User = UserFactory.build(id=uuid.uuid4())
    await logger.record("create", resource)
    db_fixture.add(resource)

    audit = await fetch_single_audit_log(db_fixture)

    assert audit.action == "create"
    assert audit.actor_type == ActorType.ANONYMOUS
    assert audit.actor_id is None

    assert audit.request_ip_address == "203.0.113.10"
    assert audit.request_user_agent == "pytest-agent"
    assert audit.request_method == "POST"
    assert str(audit.request_url).endswith("/some/path?x=1")

    assert audit.resource_type == "users"
    assert str(audit.resource_id) == str(resource.id)

    assert audit.new_value is not None
    assert audit.new_value["id"] == str(resource.id)
    assert audit.old_value is None


@pytest.mark.asyncio
async def test_audit_logger_delete_records_anonymous_actor_and_old_value(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator, request_fixture: Request
):
    logger = AuditLogger(request=request_fixture, authenticator=authenticator_fixture, db=db_fixture)
    resource: User = UserFactory.build(id=uuid.uuid4())
    await logger.record("delete", resource)
    db_fixture.add(resource)

    audit = await fetch_single_audit_log(db_fixture)

    assert audit.action == "delete"
    assert audit.actor_type == ActorType.ANONYMOUS
    assert audit.actor_id is None

    assert audit.request_ip_address == "203.0.113.10"
    assert audit.request_user_agent == "pytest-agent"
    assert audit.request_method == "POST"
    assert str(audit.request_url).endswith("/some/path?x=1")
    assert audit.resource_type == "users"
    assert str(audit.resource_id) == str(resource.id)

    assert audit.new_value is None
    assert audit.old_value is not None
    assert audit.old_value["id"] == str(resource.id)


@pytest.mark.asyncio
async def test_audit_logger_uses_user_actor_when_token_is_valid(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    user: User = UserFactory.build(id=uuid.uuid4())
    token, _ = authenticator_fixture.encode(user)
    request = make_request_with_token(token)

    logger = AuditLogger(request=request, authenticator=authenticator_fixture, db=db_fixture)
    resource: User = UserFactory.build(id=uuid.uuid4())
    await logger.record("update", resource)
    db_fixture.add(resource)

    audit = await fetch_single_audit_log(db_fixture)
    assert audit.action == "update"
    assert audit.actor_type == ActorType.USER
    assert str(audit.actor_id) == str(user.id)

    assert audit.request_ip_address == "203.0.113.10"
    assert audit.request_user_agent == "pytest-agent"
    assert audit.request_method == "POST"
    assert str(audit.request_url).endswith("/some/path?x=1")

    assert audit.resource_type == "users"
    assert str(audit.resource_id) == str(resource.id)
    assert audit.new_value is not None
    assert audit.new_value["id"] == str(resource.id)
    assert audit.old_value is None


@pytest.mark.asyncio
async def test_audit_logger_defaults_to_anonymous_actor_when_token_invalid(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator
):
    request = make_request_with_token("invalid-token")

    logger = AuditLogger(request=request, authenticator=authenticator_fixture, db=db_fixture)
    resource: User = UserFactory.build(id=uuid.uuid4())
    await logger.record("create", resource)
    db_fixture.add(resource)

    audit = await fetch_single_audit_log(db_fixture)
    assert audit.action == "create"
    assert audit.actor_type == ActorType.ANONYMOUS
    assert audit.actor_id is None

    assert audit.request_ip_address == "203.0.113.10"
    assert audit.request_user_agent == "pytest-agent"
    assert audit.request_method == "POST"
    assert str(audit.request_url).endswith("/some/path?x=1")
    assert audit.resource_type == "users"
    assert str(audit.resource_id) == str(resource.id)
    assert audit.new_value is not None
    assert audit.new_value["id"] == str(resource.id)
    assert audit.old_value is None


@pytest.mark.asyncio
async def test_audit_logger_update_records_old_new_and_changed_values_after_track(
    db_fixture: AsyncSession, authenticator_fixture: Authenticator, request_fixture: Request
):
    logger = AuditLogger(request=request_fixture, authenticator=authenticator_fixture, db=db_fixture)
    resource: User = UserFactory.build(id=uuid.uuid4(), email="user@example.com")
    await logger.track(resource)

    # Simulate an update to the resource
    resource.email = "newuser@example.com"
    await logger.record("update", resource)
    db_fixture.add(resource)

    audit = await fetch_single_audit_log(db_fixture)
    assert audit.action == "update"
    assert audit.actor_type == ActorType.ANONYMOUS
    assert audit.actor_id is None
    assert audit.request_ip_address == "203.0.113.10"
    assert audit.request_user_agent == "pytest-agent"
    assert audit.request_method == "POST"
    assert str(audit.request_url).endswith("/some/path?x=1")
    assert audit.resource_type == "users"
    assert str(audit.resource_id) == str(resource.id)
    assert audit.new_value is not None
    assert audit.new_value["id"] == str(resource.id)
    assert audit.old_value is not None
    assert audit.old_value["id"] == str(resource.id)
    assert audit.changed_value is not None
    assert "values_changed" in audit.changed_value
    assert isinstance(audit.changed_value["values_changed"], dict)
    assert audit.changed_value["values_changed"]["root['email']"] == {
        "old_value": "user@example.com",
        "new_value": "newuser@example.com",
    }
