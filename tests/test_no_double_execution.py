"""
Regression: internal tools (e.g. add_calendar_event) used to run TWICE per
LLM call — once inside the Brain's chat loop and once again in the
orchestrator's _execute_tools. The contract now is: the Brain executes all
data tools; the host layer only acts on stop_listening / analyze_screen.
"""
from assistant.mcp.manager import MCPManager


def test_execute_tool_sync_runs_internal_tool_exactly_once():
    m = MCPManager()
    calls = []
    m.register_internal_tool(
        "fake_tool",
        lambda **kw: calls.append(kw) or "done",
        {"type": "function", "function": {"name": "fake_tool",
                                          "description": "t",
                                          "parameters": {"type": "object", "properties": {}}}},
    )

    result = m.execute_tool_sync("fake_tool", {"x": 1})

    assert result == "done"
    assert calls == [{"x": 1}], f"expected exactly one execution, got {len(calls)}"


def test_unknown_tool_reports_error_dict():
    m = MCPManager()
    result = m.execute_tool_sync("no_such_tool", {})
    assert isinstance(result, dict) and result.get("error")


def test_orchestrator_source_does_not_reexecute_data_tools():
    """The orchestrator must not call execute_tool for data tools anymore."""
    from pathlib import Path
    src = Path("assistant/core/orchestrator.py").read_text(encoding="utf-8")
    body = src.split("async def _execute_tools", 1)[1].split("async def", 1)[0]
    assert "execute_tool(" not in body, \
        "_execute_tools re-executing data tools would double every side effect"
