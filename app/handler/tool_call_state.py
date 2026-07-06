from typing import Optional


_TOOL_CALL_THOUGHT_SIGNATURES: dict[str, str] = {}


def remember_thought_signature(tool_call_id: str, thought_signature: Optional[str]) -> None:
    if tool_call_id and thought_signature:
        _TOOL_CALL_THOUGHT_SIGNATURES[tool_call_id] = thought_signature


def get_thought_signature(tool_call_id: Optional[str]) -> Optional[str]:
    if not tool_call_id:
        return None
    return _TOOL_CALL_THOUGHT_SIGNATURES.get(tool_call_id)
