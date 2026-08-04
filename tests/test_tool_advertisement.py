"""
Regression: during the MCP refactor the desktop skills (open_app & friends)
silently dropped out of the tool list advertised to the LLM — "Spotify'ı aç"
became impossible for months and nothing noticed. This test pins the skills
into the advertised tool set forever.
"""
from assistant.mcp.manager import MCPManager

SKILL_TOOLS = {
    "open_app", "close_app", "open_url",
    "take_screenshot", "set_volume", "run_shortcut",
}


def _fresh_manager():
    m = MCPManager()
    m.ensure_default_tools()
    return m


def test_skill_tools_are_advertised():
    m = _fresh_manager()
    names = {t["function"]["name"] for t in m.get_all_tools() if "function" in t}
    missing = SKILL_TOOLS - names
    assert not missing, f"Skills missing from LLM tool list: {missing}"


def test_skill_tools_are_executable():
    m = _fresh_manager()
    for name in SKILL_TOOLS:
        assert m.has_tool(name), f"{name} advertised but not executable"


def test_ensure_default_tools_is_idempotent():
    m = _fresh_manager()
    first = len(m.get_all_tools())
    m.ensure_default_tools()
    m.ensure_default_tools()
    assert len(m.get_all_tools()) == first
