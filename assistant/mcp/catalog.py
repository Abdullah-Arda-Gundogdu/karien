"""
MCP Catalog - Curated list of recommended MCP servers.

This catalog provides a curated list of MCP servers that work well with Karien.
Users can install MCPs from this catalog or add custom ones.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from assistant.core.logging_config import logger


@dataclass  
class CatalogEntry:
    """Represents an MCP available for installation."""
    id: str
    name: str
    description: str
    command: str
    platforms: list[str]
    category: str
    recommended: bool = False
    tools_provided: list[str] = None
    config_schema: dict = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "CatalogEntry":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            command=data["command"],
            platforms=data.get("platform", data.get("platforms", [])),
            category=data.get("category", "other"),
            recommended=data.get("recommended", False),
            tools_provided=data.get("tools_provided"),
            config_schema=data.get("config_schema"),
        )
    
    def requires_config(self) -> bool:
        """Check if this MCP requires environment configuration."""
        if not self.config_schema:
            return False
        env_config = self.config_schema.get("env", {})
        return any(v.get("required", False) for v in env_config.values())
    
    def get_env_schema(self) -> dict:
        """Get the environment variable schema for this MCP."""
        if not self.config_schema:
            return {}
        return self.config_schema.get("env", {})

    def get_validation_config(self) -> dict | None:
        """Get validation configuration if available."""
        if not self.config_schema:
            return None
        return self.config_schema.get("validation")


class MCPCatalog:
    """
    Loads and provides access to the curated MCP catalog.
    
    The catalog is a JSON file containing recommended MCP servers.
    """
    
    def __init__(self, catalog_path: Path):
        self.catalog_path = catalog_path
        self._entries: dict[str, CatalogEntry] = {}
        self._load()
    
    def _load(self) -> None:
        """Load catalog from disk."""
        if self.catalog_path.exists():
            try:
                data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
                for entry_data in data.get("mcps", []):
                    entry = CatalogEntry.from_dict(entry_data)
                    self._entries[entry.id] = entry
                logger.info(f"Loaded {len(self._entries)} MCPs from catalog")
            except Exception as e:
                logger.error(f"Failed to load MCP catalog: {e}")
                self._entries = {}
        else:
            logger.warning(f"MCP catalog not found at {self.catalog_path}")
    
    def get_all(self) -> list[CatalogEntry]:
        """Get all catalog entries."""
        return list(self._entries.values())
    
    def get_for_platform(self, platform: str) -> list[CatalogEntry]:
        """Get catalog entries compatible with the given platform."""
        return [
            e for e in self._entries.values() 
            if platform in e.platforms or "all" in e.platforms
        ]
    
    def get_recommended(self, platform: str) -> list[CatalogEntry]:
        """Get recommended MCPs for the given platform."""
        return [
            e for e in self.get_for_platform(platform)
            if e.recommended
        ]
    
    def get(self, mcp_id: str) -> Optional[CatalogEntry]:
        """Get a specific catalog entry by ID."""
        return self._entries.get(mcp_id)
    
    def reload(self) -> None:
        """Reload catalog from disk."""
        self._entries.clear()
        self._load()
