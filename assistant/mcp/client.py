"""
MCP Client Wrapper - Manages connection to individual MCP servers.

Wraps the MCP Python SDK to provide:
- Async connection management
- Tool discovery
- Tool execution
- Graceful error handling
"""

import asyncio
import platform
from typing import Any, Optional
from dataclasses import dataclass, field
from assistant.core.logging_config import logger

# MCP SDK imports - will be installed via requirements.txt
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not installed. Install with: pip install mcp")


@dataclass
class MCPTool:
    """Represents a tool provided by an MCP server."""
    name: str
    description: str
    input_schema: dict
    mcp_id: str  # Which MCP provides this tool
    
    def to_openai_format(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }


class MCPClientWrapper:
    """
    Manages connection to a single MCP server via stdio.
    
    Handles:
    - Starting/stopping the MCP server process
    - Listing available tools
    - Executing tool calls
    """
    
    def __init__(self, mcp_id: str, command: str, env: dict = None, env_keys: list = None):
        self.mcp_id = mcp_id
        self.command = command
        self.env = env or {}
        self.env_keys = env_keys or []  # List of secret keys stored in keyring
        
        self._session: Optional[ClientSession] = None
        self._tools: list[MCPTool] = []
        self._connected = False
        self._client_context = None
        self._session_context = None
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def tools(self) -> list[MCPTool]:
        return self._tools
    
    async def connect(self, timeout: float = 30.0) -> bool:
        """
        Connect to the MCP server and discover available tools.
        
        Args:
            timeout: Maximum seconds to wait for connection
            
        Returns:
            True if connection successful, False otherwise
        """
        if not MCP_AVAILABLE:
            logger.error(f"Cannot connect to MCP {self.mcp_id}: MCP SDK not installed")
            return False
        
        if self._connected:
            logger.warning(f"MCP {self.mcp_id} already connected")
            return True
        
        try:
            logger.info(f"Connecting to MCP: {self.mcp_id} ({self.command})")
            
            # Parse command into executable and args
            parts = self.command.split()
            executable = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Resolve executable path (important for Windows npx -> npx.cmd)
            import shutil
            resolved_path = shutil.which(executable)
            if resolved_path:
                executable = resolved_path
                logger.debug(f"Resolved command {parts[0]} to {resolved_path}")
            elif not MCP_AVAILABLE: # Just in case check
                pass
            else:
                # If not found, explicitly check for npx.cmd on Windows as fallback
                if platform.system() == "Windows" and executable == "npx":
                    npx_cmd = shutil.which("npx.cmd")
                    if npx_cmd:
                        executable = npx_cmd
                        logger.debug(f"Resolved npx to {npx_cmd}")
            
            # Create server parameters
            # Merge OS environment with custom env and secrets
            import os
            from assistant.mcp.secrets_manager import secrets_manager
            
            merged_env = {**os.environ}  # Start with OS environment
            
            # Add secrets from keyring for this MCP
            if self.env:
                # Get secret keys that should be fetched from keyring
                for key, value in self.env.items():
                    if value:  # If value provided directly, use it
                        merged_env[key] = value
                    else:  # Otherwise try to get from secrets
                        secret = secrets_manager.get(self.mcp_id, key)
                        if secret:
                            merged_env[key] = secret
            
            # Fetch secrets from keyring for configured env keys
            for env_key in self.env_keys:
                secret = secrets_manager.get(self.mcp_id, env_key)
                if secret and env_key not in merged_env:
                    merged_env[env_key] = secret
            
            server_params = StdioServerParameters(
                command=executable,
                args=args,
                env=merged_env,
            )
            
            # Connect with timeout
            async with asyncio.timeout(timeout):
                # Create client and session
                self._client_context = stdio_client(server_params)
                read, write = await self._client_context.__aenter__()
                
                self._session_context = ClientSession(read, write)
                self._session = await self._session_context.__aenter__()
                
                # Initialize session
                await self._session.initialize()
                
                # Discover tools
                await self._discover_tools()
                
                self._connected = True
                logger.info(f"Connected to MCP {self.mcp_id}, found {len(self._tools)} tools")
                return True
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to MCP {self.mcp_id}")
            await self._cleanup()
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MCP {self.mcp_id}: {e}")
            await self._cleanup()
            return False
    
    async def _discover_tools(self) -> None:
        """Fetch available tools from the MCP server."""
        if not self._session:
            return
        
        try:
            result = await self._session.list_tools()
            self._tools = []
            
            for tool in result.tools:
                mcp_tool = MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    mcp_id=self.mcp_id,
                )
                self._tools.append(mcp_tool)
                logger.debug(f"Discovered tool: {tool.name}")
                
        except Exception as e:
            logger.error(f"Failed to discover tools from MCP {self.mcp_id}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: dict, timeout: float = 60.0) -> Any:
        """
        Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            timeout: Maximum seconds to wait for execution
            
        Returns:
            Tool execution result
            
        Raises:
            RuntimeError: If not connected or tool execution fails
        """
        if not self._connected or not self._session:
            raise RuntimeError(f"MCP {self.mcp_id} not connected")
        
        try:
            logger.info(f"Calling MCP tool: {tool_name} with args: {arguments}")
            
            async with asyncio.timeout(timeout):
                result = await self._session.call_tool(tool_name, arguments)
                logger.debug(f"Tool {tool_name} result: {result}")
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout executing tool {tool_name} on MCP {self.mcp_id}")
            raise RuntimeError(f"Tool execution timeout: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            raise RuntimeError(f"Tool execution failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if not self._connected:
            return
        
        logger.info(f"Disconnecting from MCP: {self.mcp_id}")
        await self._cleanup()
        self._connected = False
    
    async def _cleanup(self) -> None:
        """Clean up session and client contexts."""
        try:
            if self._session_context:
                # We need to be careful with context exit order and task cancellation
                try:
                    await self._session_context.__aexit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Session context exit: {e}")
                self._session_context = None
                
            if self._client_context:
                try:
                    await self._client_context.__aexit__(None, None, None)
                except RuntimeError as re:
                    # Ignore 'Attempted to exit cancel scope' error which happens frequently
                    # with anyio/asyncio interop during shutdown
                    if "cancel scope" not in str(re):
                        logger.warning(f"Client context runtime error: {re}")
                except Exception as e:
                    logger.debug(f"Client context exit: {e}")
                self._client_context = None
                
            self._session = None
        except Exception as e:
            logger.warning(f"Error during MCP cleanup: {e}")
