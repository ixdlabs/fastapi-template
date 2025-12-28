from inspect import Parameter, Signature


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
    param = next((p for p in signature.parameters.values() if p.annotation is dep.annotation), None)
    if param is None:
        to_inject.append(dep)
        param = dep
    return param
