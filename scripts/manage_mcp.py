
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock OpenAI Key to bypass config validation
import os
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-mcp-management"

from assistant.mcp.manager import mcp_manager

async def list_mcps():
    print("\n=== Available MCPs (Catalog) ===")
    for mcp in mcp_manager.get_available_for_install():
        installed = mcp_manager._registry.is_installed(mcp.id)
        status = "[INSTALLED]" if installed else "[ ]"
        print(f"{status} {mcp.id}: {mcp.description}")

    print("\n=== Installed MCPs ===")
    for mcp in mcp_manager.get_installed():
        status = "[ENABLED]" if mcp.enabled else "[DISABLED]"
        print(f"{status} {mcp.id} ({mcp.name})")

async def install_mcp(mcp_id):
    print(f"Installing {mcp_id}...")
    success = await mcp_manager.install_from_catalog(mcp_id)
    if success:
        print(f"Successfully installed {mcp_id}")
    else:
        print(f"Failed to install {mcp_id}")

async def uninstall_mcp(mcp_id):
    print(f"Uninstalling {mcp_id}...")
    success = await mcp_manager.uninstall(mcp_id)
    if success:
        print(f"Successfully uninstalled {mcp_id}")
    else:
        print(f"Failed to uninstall {mcp_id}")

async def test_mcp(mcp_id):
    print(f"\nTesting connection to {mcp_id}...")
    
    # 1. Check registry
    if not mcp_manager._registry.is_installed(mcp_id):
        print(f"Error: {mcp_id} is not installed.")
        return

    # 2. Initialize Manager (connects to enabled MCPs)
    print("Initializing Manager...")
    await mcp_manager.initialize()
    
    # 3. Check connection
    full_tool_list = mcp_manager.get_all_tools()
    
    # Filter tools for this MCP
    client = mcp_manager._clients.get(mcp_id)
    if client and client.is_connected:
        print(f"\n[OK] Successfully connected to {mcp_id}!")
        print(f"Available Tools ({len(client.tools)}):")
        for tool in client.tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
            
        # Try a simple execution if it's the 'time' MCP
        if mcp_id == "time":
            # The tool name for @modelcontextprotocol/server-time is usually 'mcp_time_get_current_time' or similar
            # But let's check what we actually got
            target_tool = next((t.name for t in client.tools if "time" in t.name.lower()), None)
            
            if target_tool:
                print(f"\nRunning test tool: {target_tool}...")
                try:
                    # Generic empty args
                    args = {} 
                    result = await mcp_manager.execute_tool(target_tool, args)
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Tool execution failed: {e}")
            
    else:
        print(f"[FAILED] Failed to connect to {mcp_id}")

    # Cleanup
    await mcp_manager.shutdown()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_mcp.py [list|install <id>|uninstall <id>|test <id>]")
        return

    command = sys.argv[1]
    
    # Initialize implementation
    mcp_manager._ensure_loaded()

    if command == "list":
        await list_mcps()
    elif command == "install" and len(sys.argv) > 2:
        await install_mcp(sys.argv[2])
    elif command == "uninstall" and len(sys.argv) > 2:
        await uninstall_mcp(sys.argv[2])
    elif command == "test" and len(sys.argv) > 2:
        await test_mcp(sys.argv[2])
    else:
        print("Invalid command")

if __name__ == "__main__":
    asyncio.run(main())
