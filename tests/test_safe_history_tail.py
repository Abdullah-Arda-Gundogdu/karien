"""
Regression: naive history[-n:] slicing could split an assistant tool_calls
message from its role:"tool" results, which the OpenAI API rejects with 400.
"""
from assistant.brain.worker import safe_history_tail


def _turn(i):
    return [
        {"role": "user", "content": f"q{i}"},
        {"role": "assistant", "content": f"a{i}"},
    ]


def _tool_turn(i):
    return [
        {"role": "user", "content": f"q{i}"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": f"call_{i}", "type": "function",
                         "function": {"name": "open_app", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": f"call_{i}", "name": "open_app", "content": "ok"},
        {"role": "assistant", "content": f"done {i}"},
    ]


def test_window_never_starts_on_tool_message():
    history = [{"role": "system", "content": "sys"}] + _turn(1) + _tool_turn(2)
    # n=3 would naively start at the tool result — the parent must be pulled in
    tail = safe_history_tail(history, 3)
    assert tail[0].get("role") != "tool"
    roles = [m["role"] for m in tail]
    if "tool" in roles:
        assert roles.index("tool") > 0
        parent = tail[roles.index("tool") - 1]
        assert parent["role"] == "assistant" and parent.get("tool_calls")


def test_dangling_tool_calls_are_stripped():
    # A turn that crashed mid-execution: tool_calls with no tool result
    history = _turn(1) + [
        {"role": "user", "content": "aç"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "call_x", "type": "function",
                         "function": {"name": "open_app", "arguments": "{}"}}]},
    ]
    tail = safe_history_tail(history, 10)
    for m in tail:
        assert not (m.get("role") == "assistant" and m.get("tool_calls")), \
            "unresolved tool_calls must not survive"


def test_orphan_tool_results_are_dropped():
    history = [
        {"role": "tool", "tool_call_id": "ghost", "name": "x", "content": "?"},
    ] + _turn(1)
    tail = safe_history_tail(history, 10)
    assert all(m.get("role") != "tool" for m in tail)


def test_excludes_system_and_respects_limit():
    history = [{"role": "system", "content": "sys"}] + _turn(1) + _turn(2) + _turn(3)
    tail = safe_history_tail(history, 4)
    assert all(m["role"] != "system" for m in tail)
    assert len(tail) <= 4
