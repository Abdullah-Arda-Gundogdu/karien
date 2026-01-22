
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

async def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_mcp.py [list|install <id>|uninstall <id>]")
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
    else:
        print("Invalid command")

if __name__ == "__main__":
    asyncio.run(main())
