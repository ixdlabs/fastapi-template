from inspect import Parameter, Signature

import pytest

from app.core.helpers import inspect_augment_signature, inspect_locate_param, run_as_sync

# Tests for inspect_augment_signature
# ----------------------------------------------------------------------------------------------------------------------


def test_inspect_augment_signature_no_extra_returns_original():
    sig = Signature(
        parameters=[
            Parameter("a", kind=Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("b", kind=Parameter.POSITIONAL_OR_KEYWORD),
        ]
    )

    new_sig = inspect_augment_signature(sig)

    assert new_sig is sig


def test_inspect_augment_signature_appends_extra_parameters():
    sig = Signature(parameters=[Parameter("a", kind=Parameter.POSITIONAL_OR_KEYWORD)])
    extra = Parameter("x", kind=Parameter.POSITIONAL_OR_KEYWORD)

    new_sig = inspect_augment_signature(sig, extra)

    assert list(new_sig.parameters) == ["a", "x"]


def test_inspect_augment_signature_inserts_before_var_keyword():
    sig = Signature(
        parameters=[
            Parameter("a", kind=Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("kwargs", kind=Parameter.VAR_KEYWORD),
        ]
    )
    extra1 = Parameter("x", kind=Parameter.POSITIONAL_OR_KEYWORD)
    extra2 = Parameter("y", kind=Parameter.POSITIONAL_OR_KEYWORD)

    new_sig = inspect_augment_signature(sig, extra1, extra2)

    assert list(new_sig.parameters) == ["a", "x", "y", "kwargs"]
    assert new_sig.parameters["kwargs"].kind is Parameter.VAR_KEYWORD


def test_inspect_augment_signature_multiple_var_keyword_preserved():
    sig = Signature(
        parameters=[
            Parameter("a", kind=Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("kwargs1", kind=Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("kwargs2", kind=Parameter.VAR_KEYWORD),
        ]
    )
    extra = Parameter("x", kind=Parameter.POSITIONAL_OR_KEYWORD)

    new_sig = inspect_augment_signature(sig, extra)

    assert set(new_sig.parameters) == {"a", "x", "kwargs1", "kwargs2"}


# Tests for inspect_locate_param
# ----------------------------------------------------------------------------------------------------------------------


def test_inspect_locate_param_finds_existing_by_annotation():
    class Dep:
        pass

    existing = Parameter("dep", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Dep)
    sig = Signature(parameters=[existing])
    to_inject = []

    dep_param = Parameter("dep_injected", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Dep)

    result = inspect_locate_param(sig, dep_param, to_inject)

    assert result is existing
    assert to_inject == []


def test_inspect_locate_param_adds_when_missing():
    class Dep:
        pass

    sig = Signature(parameters=[Parameter("a", kind=Parameter.POSITIONAL_OR_KEYWORD)])
    to_inject = []

    dep_param = Parameter("dep", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Dep)

    result = inspect_locate_param(sig, dep_param, to_inject)

    assert result is dep_param
    assert to_inject == [dep_param]


def test_inspect_locate_param_ignores_name_and_matches_only_annotation():
    class Dep:
        pass

    existing = Parameter("x", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Dep)
    sig = Signature(parameters=[existing])
    to_inject = []

    dep_param = Parameter("y", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Dep)

    result = inspect_locate_param(sig, dep_param, to_inject)

    assert result is existing
    assert to_inject == []


# Tests for run_as_sync
# ----------------------------------------------------------------------------------------------------------------------


# Tests for TaskRegistry
# ----------------------------------------------------------------------------------------------------------------------


def test_background_task_runs_synchronously_when_event_loop_missing():
    async def sample_task(x: int, y: int) -> int:
        return x + y

    result = run_as_sync(sample_task, 2, 3)
    assert result == 5


@pytest.mark.asyncio
async def test_background_task_runs_as_coroutine_when_event_loop_present():
    async def sample_task(x: int, y: int) -> int:
        return x + y

    result = run_as_sync(sample_task, 4, 5)
    assert result == 9


@pytest.mark.asyncio
async def test_background_task_propagates_errors_from_wrapped_coroutine():
    async def error_task():
        raise ValueError("Intentional error")

    with pytest.raises(ValueError, match="Intentional error"):
        run_as_sync(error_task)
