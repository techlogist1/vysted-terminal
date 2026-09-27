import sys, os, asyncio
os.environ["VYSTED_SIDECAR_INTERNAL_BASE_URL"] = "http://127.0.0.1:52398"
sys.path.insert(0, "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand/sidecar")
from services import mcp_server

async def main():
    print("=== R15-AGENT-059: list_agents/list_workflows/list_runs against a 500 upstream ===")
    r1 = await mcp_server._get_list("/agents", "agents")
    print("  _get_list('/agents', 'agents') ->", r1)
    r2 = await mcp_server._get_list("/workflow/saved", "workflows")
    print("  _get_list('/workflow/saved', 'workflows') ->", r2)
    r3 = await mcp_server._get_list("/runs", "runs")
    print("  _get_list('/runs', 'runs') ->", r3)
    assert r1.get("ok") is False and "agents" not in r1, "list_agents must not degrade to empty list"
    assert r2.get("ok") is False
    assert r3.get("ok") is False
    print("  PASS: all three report ok:false on a 500, none silently returns an empty list")

    print()
    print("=== R15-CODE-AGENT-012: invoke_agent MCP tool schema has no api_key parameter ===")
    server = mcp_server.get_mcp_server()
    tools_list = await server.list_tools()
    tools = {t.name: t for t in tools_list}
    invoke_tool = tools.get("invoke_agent")
    print("  invoke_agent parameters schema:", invoke_tool.parameters)
    props = invoke_tool.parameters.get("properties", {})
    assert "api_key" not in props, "api_key must not be a published tool argument"
    print("  PASS: api_key is not in the published tool schema; properties =", list(props.keys()))

asyncio.run(main())
