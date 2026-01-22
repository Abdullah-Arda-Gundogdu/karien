"""
MCP Registry - Persistent storage for installed MCPs.

Manages the state of installed MCPs including:
- Installation/uninstallation tracking
- Enable/disable state
- Per-MCP configuration
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from assistant.core.logging_config import logger


@dataclass
class MCPEntry:
    """Represents an installed MCP server."""
    id: str
    name: str
    description: str
    command: str
    platforms: list[str]
    category: str
    enabled: bool = True
    config: dict = field(default_factory=dict)
    tools_provided: list[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MCPEntry":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            command=data["command"],
            platforms=data.get("platforms", data.get("platform", [])),
            category=data.get("category", "other"),
            enabled=data.get("enabled", True),
            config=data.get("config", {}),
            tools_provided=data.get("tools_provided", []),
        )
    
    def to_dict(self) -> dict:
        return asdict(self)


class MCPRegistry:
    """
    Manages persistent state for installed MCP servers.
    
    State is stored in a JSON file at the configured path.
    """
    
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self._entries: dict[str, MCPEntry] = {}
        self._load()
    
    def _load(self) -> None:
        """Load registry from disk, or create from template if missing."""
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                for entry_data in data.get("installed", []):
                    entry = MCPEntry.from_dict(entry_data)
                    self._entries[entry.id] = entry
                logger.info(f"Loaded {len(self._entries)} MCPs from registry")
            except Exception as e:
                logger.error(f"Failed to load MCP registry: {e}")
                self._entries = {}
        else:
            # Try to copy from template
            template_path = self.registry_path.parent / "mcp_registry.example.json"
            if template_path.exists():
                import shutil
                self.registry_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(template_path, self.registry_path)
                logger.info("Created MCP registry from template")
            else:
                # Create empty registry
                self._save()
                logger.info("Created empty MCP registry")
    
    def _save(self) -> None:
        """Persist registry to disk."""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "installed": [entry.to_dict() for entry in self._entries.values()]
            }
            self.registry_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.debug(f"Saved MCP registry with {len(self._entries)} entries")
        except Exception as e:
            logger.error(f"Failed to save MCP registry: {e}")
    
    def get_all(self) -> list[MCPEntry]:
        """Get all installed MCPs."""
        return list(self._entries.values())
    
    def get_enabled(self) -> list[MCPEntry]:
        """Get only enabled MCPs."""
        return [e for e in self._entries.values() if e.enabled]
    
    def get(self, mcp_id: str) -> Optional[MCPEntry]:
        """Get a specific MCP by ID."""
        return self._entries.get(mcp_id)
    
    def install(self, entry: MCPEntry) -> None:
        """Install (add) an MCP to the registry."""
        self._entries[entry.id] = entry
        self._save()
        logger.info(f"Installed MCP: {entry.id}")
    
    def uninstall(self, mcp_id: str) -> bool:
        """Remove an MCP from the registry."""
        if mcp_id in self._entries:
            del self._entries[mcp_id]
            self._save()
            logger.info(f"Uninstalled MCP: {mcp_id}")
            return True
        return False
    
    def enable(self, mcp_id: str) -> bool:
        """Enable an MCP."""
        if mcp_id in self._entries:
            self._entries[mcp_id].enabled = True
            self._save()
            logger.info(f"Enabled MCP: {mcp_id}")
            return True
        return False
    
    def disable(self, mcp_id: str) -> bool:
        """Disable an MCP."""
        if mcp_id in self._entries:
            self._entries[mcp_id].enabled = False
            self._save()
            logger.info(f"Disabled MCP: {mcp_id}")
            return True
        return False
    
    def update_config(self, mcp_id: str, config: dict) -> bool:
        """Update configuration for an MCP."""
        if mcp_id in self._entries:
            self._entries[mcp_id].config = config
            self._save()
            logger.info(f"Updated config for MCP: {mcp_id}")
            return True
        return False
    
    def is_installed(self, mcp_id: str) -> bool:
        """Check if an MCP is installed."""
        return mcp_id in self._entries
