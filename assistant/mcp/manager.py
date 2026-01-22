"""
MCP Manager - Central orchestration layer for all MCP operations.

This is the main entry point for MCP functionality, providing:
- Unified tool interface for Brain/LLM
- Lifecycle management (start/stop MCPs)
- Platform-aware MCP selection
- Fallback to internal tools when MCP fails
"""

import asyncio
import platform
from pathlib import Path
from typing import Any, Optional, Callable
from assistant.core.logging_config import logger
from assistant.mcp.registry import MCPRegistry, MCPEntry
from assistant.mcp.catalog import MCPCatalog, CatalogEntry
from assistant.mcp.client import MCPClientWrapper, MCPTool


class MCPManager:
    """
    Central manager for all MCP servers.
    
    Provides:
    - Tool discovery from enabled MCPs
    - Tool execution with fallback support
    - Platform-aware MCP filtering
    """
    
    def __init__(self):
        # Lazy-load paths from config to avoid circular imports
        self._registry: Optional[MCPRegistry] = None
        self._catalog: Optional[MCPCatalog] = None
        self._clients: dict[str, MCPClientWrapper] = {}
        self._initialized = False
        self._internal_tools: dict[str, Callable] = {}
        self._tool_to_mcp: dict[str, str] = {}  # Maps tool name to MCP ID
        
        # Platform detection
        system = platform.system().lower()
        if system == "darwin":
            self._platform = "darwin"
        elif system == "windows":
            self._platform = "windows"
        else:
            self._platform = system
        
        logger.info(f"MCPManager created for platform: {self._platform}")
    
    def _ensure_loaded(self) -> None:
        """Lazy load registry and catalog."""
        if self._registry is None:
            from assistant.core.config import config
            self._registry = MCPRegistry(config.MCP_REGISTRY_PATH)
            self._catalog = MCPCatalog(config.MCP_CATALOG_PATH)
    
    @property
    def platform(self) -> str:
        """Current platform identifier."""
        return self._platform
    
    @property
    def is_initialized(self) -> bool:
        """Whether MCPs have been initialized."""
        return self._initialized
    
    def register_internal_tool(self, name: str, handler: Callable) -> None:
        """
        Register an internal (Python-based) tool as fallback.
        
        Args:
            name: Tool name (should match MCP tool name for fallback)
            handler: Async or sync callable that executes the tool
        """
        self._internal_tools[name] = handler
        logger.debug(f"Registered internal tool: {name}")
    
    async def initialize(self) -> None:
        """
        Initialize all enabled MCPs.
        
        This should be called at app startup. It runs asynchronously
        and does not block the main application.
        """
        if self._initialized:
            logger.warning("MCPManager already initialized")
            return
        
        self._ensure_loaded()
        
        logger.info("Initializing MCP Manager...")
        
        enabled_mcps = self._registry.get_enabled()
        if not enabled_mcps:
            logger.info("No enabled MCPs to initialize")
            self._initialized = True
            return
        
        # Connect to each enabled MCP concurrently
        connect_tasks = []
        for mcp in enabled_mcps:
            if self._platform not in mcp.platforms:
                logger.warning(f"Skipping MCP {mcp.id}: not compatible with {self._platform}")
                continue
            
            client = MCPClientWrapper(mcp.id, mcp.command, mcp.config.get("env"))
            self._clients[mcp.id] = client
            connect_tasks.append(self._connect_with_retry(client))
        
        if connect_tasks:
            results = await asyncio.gather(*connect_tasks, return_exceptions=True)
            successes = sum(1 for r in results if r is True)
            logger.info(f"Connected to {successes}/{len(connect_tasks)} MCP servers")
        
        # Build tool-to-MCP mapping
        self._build_tool_mapping()
        
        self._initialized = True
        logger.info("MCP Manager initialized")
    
    async def _connect_with_retry(self, client: MCPClientWrapper, retries: int = 2) -> bool:
        """Attempt to connect to MCP with retries."""
        for attempt in range(retries + 1):
            if await client.connect():
                return True
            if attempt < retries:
                logger.warning(f"Retrying connection to {client.mcp_id}...")
                await asyncio.sleep(1)
        return False
    
    def _build_tool_mapping(self) -> None:
        """Build mapping from tool names to MCP IDs."""
        self._tool_to_mcp.clear()
        for mcp_id, client in self._clients.items():
            if client.is_connected:
                for tool in client.tools:
                    self._tool_to_mcp[tool.name] = mcp_id
    
    def get_all_tools(self) -> list[dict]:
        """
        Get all available tools in OpenAI function calling format.
        
        Aggregates tools from all connected MCPs.
        
        Returns:
            List of tool definitions in OpenAI format
        """
        tools = []
        
        for client in self._clients.values():
            if client.is_connected:
                for tool in client.tools:
                    tools.append(tool.to_openai_format())
        
        return tools
    
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Execute a tool, with fallback to internal implementation.
        
        Strategy (Option C):
        1. Try MCP tool first
        2. If fails, try internal fallback
        3. If both fail, notify with error message
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        error_message = None
        
        # 1. Try MCP tool
        if tool_name in self._tool_to_mcp:
            mcp_id = self._tool_to_mcp[tool_name]
            client = self._clients.get(mcp_id)
            
            if client and client.is_connected:
                try:
                    result = await client.call_tool(tool_name, arguments)
                    logger.info(f"MCP tool {tool_name} executed successfully")
                    return result
                except Exception as e:
                    error_message = str(e)
                    logger.warning(f"MCP tool {tool_name} failed: {e}, trying fallback...")
        
        # 2. Try internal fallback
        if tool_name in self._internal_tools:
            try:
                handler = self._internal_tools[tool_name]
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**arguments)
                else:
                    result = handler(**arguments)
                logger.info(f"Internal fallback for {tool_name} executed successfully")
                return result
            except Exception as e:
                error_message = f"Fallback also failed: {e}"
                logger.error(f"Internal fallback for {tool_name} failed: {e}")
        
        # 3. Both failed - return error info
        if error_message:
            logger.error(f"Tool {tool_name} completely failed: {error_message}")
            return {"error": True, "message": f"Tool {tool_name} failed: {error_message}"}
        else:
            logger.error(f"Unknown tool: {tool_name}")
            return {"error": True, "message": f"Unknown tool: {tool_name}"}
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available (MCP or internal)."""
        return tool_name in self._tool_to_mcp or tool_name in self._internal_tools
    
    # ==================== Management Interface ====================
    
    def get_available_for_install(self) -> list[CatalogEntry]:
        """Get MCPs from catalog that are compatible with current platform."""
        self._ensure_loaded()
        return self._catalog.get_for_platform(self._platform)
    
    def get_installed(self) -> list[MCPEntry]:
        """Get all installed MCPs."""
        self._ensure_loaded()
        return self._registry.get_all()
    
    def get_enabled(self) -> list[MCPEntry]:
        """Get enabled MCPs."""
        self._ensure_loaded()
        return self._registry.get_enabled()
    
    async def install_from_catalog(self, mcp_id: str) -> bool:
        """
        Install an MCP from the catalog.
        
        Args:
            mcp_id: ID of the MCP in the catalog
            
        Returns:
            True if installation successful
        """
        self._ensure_loaded()
        
        catalog_entry = self._catalog.get(mcp_id)
        if not catalog_entry:
            logger.error(f"MCP {mcp_id} not found in catalog")
            return False
        
        if self._platform not in catalog_entry.platforms:
            logger.error(f"MCP {mcp_id} not compatible with {self._platform}")
            return False
        
        # Create registry entry from catalog
        entry = MCPEntry(
            id=catalog_entry.id,
            name=catalog_entry.name,
            description=catalog_entry.description,
            command=catalog_entry.command,
            platforms=catalog_entry.platforms,
            category=catalog_entry.category,
            enabled=True,
            tools_provided=catalog_entry.tools_provided or [],
        )
        
        self._registry.install(entry)
        
        # Connect immediately if already initialized
        if self._initialized:
            client = MCPClientWrapper(entry.id, entry.command)
            self._clients[entry.id] = client
            if await client.connect():
                self._build_tool_mapping()
                logger.info(f"MCP {mcp_id} installed and connected")
            else:
                logger.warning(f"MCP {mcp_id} installed but failed to connect")
        
        return True
    
    async def uninstall(self, mcp_id: str) -> bool:
        """Uninstall an MCP."""
        self._ensure_loaded()
        
        # Disconnect if connected
        if mcp_id in self._clients:
            await self._clients[mcp_id].disconnect()
            del self._clients[mcp_id]
            self._build_tool_mapping()
        
        return self._registry.uninstall(mcp_id)
    
    async def enable(self, mcp_id: str) -> bool:
        """Enable an MCP and connect to it."""
        self._ensure_loaded()
        
        if not self._registry.enable(mcp_id):
            return False
        
        entry = self._registry.get(mcp_id)
        if entry and self._initialized:
            client = MCPClientWrapper(entry.id, entry.command, entry.config.get("env"))
            self._clients[entry.id] = client
            if await client.connect():
                self._build_tool_mapping()
        
        return True
    
    async def disable(self, mcp_id: str) -> bool:
        """Disable an MCP and disconnect from it."""
        self._ensure_loaded()
        
        if mcp_id in self._clients:
            await self._clients[mcp_id].disconnect()
            del self._clients[mcp_id]
            self._build_tool_mapping()
        
        return self._registry.disable(mcp_id)
    
    async def shutdown(self) -> None:
        """Disconnect from all MCP servers."""
        logger.info("Shutting down MCP Manager...")
        
        disconnect_tasks = [
            client.disconnect() for client in self._clients.values()
        ]
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self._clients.clear()
        self._tool_to_mcp.clear()
        self._initialized = False
        
        logger.info("MCP Manager shutdown complete")


# Global instance
mcp_manager = MCPManager()
