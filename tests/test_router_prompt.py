"""
Regression: ROUTER_SYSTEM_PROMPT once contained a literal JSON example with
single braces, so .format() raised KeyError '"intent"' on EVERY call and the
whole three-tier brain crashed on every turn (fixed in 2aca22e).
"""
from assistant.brain.router import ROUTER_SYSTEM_PROMPT


def test_router_prompt_formats_without_error():
    rendered = ROUTER_SYSTEM_PROMPT.format(tool_list="open_app, analyze_screen")
    assert '"intent"' in rendered
    assert "open_app, analyze_screen" in rendered
    assert "{tool_list}" not in rendered


def test_router_prompt_mentions_all_intents():
    for intent in ("conversation", "tool_call", "vision", "system", "greeting"):
        assert intent in ROUTER_SYSTEM_PROMPT
