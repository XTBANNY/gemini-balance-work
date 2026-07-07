import json
from typing import Any, Optional


_TOOL_CALL_THOUGHT_SIGNATURES: dict[str, str] = {}
_TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME_ARGS: dict[str, str] = {}
_TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME: dict[str, str] = {}


def _normalize_args(args: Any) -> str:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return args
    try:
        return json.dumps(args or {}, sort_keys=True, separators=(",", ":"))
    except TypeError:
        return str(args)


def _name_args_key(name: Optional[str], args: Any) -> Optional[str]:
    if not name:
        return None
    return f"{name}:{_normalize_args(args)}"


def remember_thought_signature(
    tool_call_id: Optional[str],
    thought_signature: Optional[str],
    name: Optional[str] = None,
    args: Any = None,
) -> None:
    if not thought_signature:
        return
    if tool_call_id:
        _TOOL_CALL_THOUGHT_SIGNATURES[tool_call_id] = thought_signature
    if name:
        _TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME[name] = thought_signature
    name_args_key = _name_args_key(name, args)
    if name_args_key:
        _TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME_ARGS[name_args_key] = thought_signature


def get_thought_signature(
    tool_call_id: Optional[str] = None,
    name: Optional[str] = None,
    args: Any = None,
) -> Optional[str]:
    if tool_call_id and tool_call_id in _TOOL_CALL_THOUGHT_SIGNATURES:
        return _TOOL_CALL_THOUGHT_SIGNATURES[tool_call_id]
    name_args_key = _name_args_key(name, args)
    if name_args_key and name_args_key in _TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME_ARGS:
        return _TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME_ARGS[name_args_key]
    if name and name in _TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME:
        return _TOOL_CALL_THOUGHT_SIGNATURES_BY_NAME[name]
    return None
