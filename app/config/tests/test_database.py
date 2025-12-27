import uuid
import pytest
from sqlalchemy import ForeignKey, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base, create_db_engine, get_db, get_db_session
from app.config.settings import Settings

from pytest import MonkeyPatch

# Base Model Testing
# ----------------------------------------------------------------------------------------------------------------------


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)

    children: Mapped[list["Child"]] = relationship(back_populates="parent")

    @hybrid_property
    def name_upper(self) -> str:
        return self.name.upper()


class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"))
    value: Mapped[str] = mapped_column(String)

    parent: Mapped[Parent] = relationship(back_populates="children")


def test_parent_model_exposes_columns_relations_and_hybrid_attributes():
    assert set(Parent.columns()) == {"id", "name"}
    assert Parent.relations() == ["children"]
    assert Parent.hybrid_properties() == ["name_upper"]


@pytest.mark.asyncio
async def test_to_dict_serializes_basic_model_fields_by_default():
    parent = Parent(name="alice")
    data = parent.to_dict()
    assert data == {"id": parent.id, "name": "alice"}


def test_to_dict_excludes_specified_fields_when_requested():
    parent = Parent(name="alice")
    data = parent.to_dict(exclude=["id"])
    assert data == {"name": "alice"}


def test_to_dict_includes_hybrid_attributes_when_enabled():
    parent = Parent(name="alice")
    data = parent.to_dict(hybrid_attributes=True)
    assert data["name_upper"] == "ALICE"


def test_to_dict_serializes_list_relationships_when_nested_option_enabled():
    parent = Parent(name="alice")
    child1 = Child(value="a", parent=parent)
    child2 = Child(value="b", parent=parent)
    parent.children = [child1, child2]

    data = parent.to_dict(nested=True)

    assert "children" in data
    assert isinstance(data["children"], list)
    assert len(data["children"]) == 2
    assert data["children"][0]["value"] in {"a", "b"}


def test_to_dict_serializes_single_relationship_when_nested_option_enabled():
    child = Child(value="x")
    parent = Parent(name="bob")
    child.parent = parent

    data = child.to_dict(nested=True)

    assert "parent" in data
    assert isinstance(data["parent"], dict)
    assert data["parent"]["name"] == "bob"


def test_to_dict_includes_nested_relations_and_hybrid_attributes_when_enabled():
    parent = Parent(name="alice")
    child = Child(value="x", parent=parent)
    parent.children = [child]

    data = parent.to_dict(nested=True, hybrid_attributes=True)

    assert data["name_upper"] == "ALICE"
    assert "children" in data
    assert isinstance(data["children"], list)
    assert data["children"][0]["value"] == "x"


def test_to_dict_serializes_uuid_subclasses_as_strings():
    class CustomUUID(uuid.UUID):
        pass

    class ModelWithCustomUUID(Base):
        __tablename__ = "model_with_custom_uuid"

        id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    instance = ModelWithCustomUUID(id=CustomUUID("12345678-1234-5678-1234-567812345678"))
    data = instance.to_dict()
    assert data["id"] == "12345678-1234-5678-1234-567812345678"


# DB Engine and Session Testing
# ----------------------------------------------------------------------------------------------------------------------


def test_create_db_engine_caches_connections_per_url_and_debug_flag(monkeypatch: MonkeyPatch):
    def mock_create_async_engine(url: str, echo: bool):
        return {"url": url, "echo": echo}

    create_db_engine.cache_clear()

    monkeypatch.setattr("app.config.database.create_async_engine", mock_create_async_engine)

    engine_one = create_db_engine("sqlite:///first.db", debug=True)
    engine_two = create_db_engine("sqlite:///first.db", debug=True)
    engine_three = create_db_engine("sqlite:///second.db", debug=False)

    assert engine_one is engine_two
    assert engine_three is not engine_one

    create_db_engine.cache_clear()


@pytest.mark.asyncio
async def test_get_db_session_yields_async_session_bound_to_given_url():
    test_settings = Settings.model_construct(database_url="sqlite+aiosqlite:///:memory:", debug=True)
    async for db in get_db_session(test_settings):
        url = getattr(db.bind, "url", None)
        assert str(url) == "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_get_db_context_manager_provides_async_session_bound_to_given_url():
    test_settings = Settings.model_construct(database_url="sqlite+aiosqlite:///:memory:", debug=True)
    async with get_db(test_settings) as db:
        url = getattr(db.bind, "url", None)
        assert str(url) == "sqlite+aiosqlite:///:memory:"
