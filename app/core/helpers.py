import asyncio
from collections.abc import Callable, Coroutine
from inspect import Parameter, Signature
import threading
from typing import ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


def inspect_augment_signature(signature: Signature, *extra: Parameter) -> Signature:
    """
    Augment a function signature by adding extra parameters before any variadic keyword parameters.

    Taken from: https://github.com/long2ice/fastapi-cache/blob/main/fastapi_cache/decorator.py
    """
    if not extra:
        return signature

    parameters = list(signature.parameters.values())
    variadic_keyword_params: list[Parameter] = []
    while parameters and parameters[-1].kind is Parameter.VAR_KEYWORD:
        variadic_keyword_params.append(parameters.pop())

    return signature.replace(parameters=[*parameters, *extra, *variadic_keyword_params])


def inspect_locate_param(signature: Signature, dep: Parameter, to_inject: list[Parameter]) -> Parameter:
    """
    Locate an existing parameter in the decorated endpoint
    If not found, returns the injectable parameter, and adds it to the to_inject list.

    Taken from: https://github.com/long2ice/fastapi-cache/blob/main/fastapi_cache/decorator.py
    """
    param = inspect_get_param(signature, dep)
    if param is None:
        to_inject.append(dep)
        param = dep
    return param


def inspect_get_param(signature: Signature, dep: Parameter) -> Parameter | None:
    """Get an existing parameter in the decorated endpoint, or None if not found."""
    return next((p for p in signature.parameters.values() if p.annotation is dep.annotation), None)


def run_as_sync(func: Callable[P, Coroutine[object, object, R]], *args: P.args, **kwargs: P.kwargs) -> R:
    """Converts an async function into a Celery task."""
    try:
        _ = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(func(*args, **kwargs))

    result_container: dict[str, R] = {}
    error_container: dict[str, BaseException] = {}

    def runner():
        try:
            result_container["result"] = asyncio.run(func(*args, **kwargs))
        except BaseException as exc:
            error_container["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in error_container:
        raise error_container["error"]
    return result_container["result"]
