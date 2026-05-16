import asyncio
import server as s


def test_mcp_instance_exists():
    assert s.mcp is not None
    assert s.BASE.startswith("http")


def test_all_five_tools_registered():
    tools = asyncio.run(s.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "get_telemetry", "get_directive",
        "send_command", "set_estop", "ask_copilot",
    }
