"""
MCP Secrets Manager - Secure storage for MCP API keys and credentials.

Uses the OS credential manager via keyring:
- Windows: Windows Credential Manager
- macOS: Keychain
"""

import keyring
from typing import Optional
from assistant.core.logging_config import logger


class MCPSecretsManager:
    """
    Manages secure storage of MCP credentials.
    
    Stores secrets in the OS credential manager, not in plain files.
    """
    
    SERVICE_NAME = "karien-mcp"
    
    @classmethod
    def set(cls, mcp_id: str, key: str, value: str) -> None:
        """
        Store a secret for an MCP.
        
        Args:
            mcp_id: The MCP identifier (e.g., "github")
            key: The secret key name (e.g., "GITHUB_TOKEN")
            value: The secret value
        """
        credential_name = f"{mcp_id}:{key}"
        try:
            keyring.set_password(cls.SERVICE_NAME, credential_name, value)
            logger.debug(f"Stored secret for {mcp_id}: {key}")
        except Exception as e:
            logger.error(f"Failed to store secret for {mcp_id}:{key}: {e}")
            raise
    
    @classmethod
    def get(cls, mcp_id: str, key: str) -> Optional[str]:
        """
        Retrieve a secret for an MCP.
        
        Args:
            mcp_id: The MCP identifier
            key: The secret key name
            
        Returns:
            The secret value, or None if not found
        """
        credential_name = f"{mcp_id}:{key}"
        try:
            return keyring.get_password(cls.SERVICE_NAME, credential_name)
        except Exception as e:
            logger.error(f"Failed to get secret for {mcp_id}:{key}: {e}")
            return None
    
    @classmethod
    def delete(cls, mcp_id: str, key: str) -> bool:
        """
        Delete a specific secret for an MCP.
        
        Args:
            mcp_id: The MCP identifier
            key: The secret key name
            
        Returns:
            True if deleted, False if not found or error
        """
        credential_name = f"{mcp_id}:{key}"
        try:
            keyring.delete_password(cls.SERVICE_NAME, credential_name)
            logger.debug(f"Deleted secret for {mcp_id}: {key}")
            return True
        except keyring.errors.PasswordDeleteError:
            # Password doesn't exist
            return False
        except Exception as e:
            logger.error(f"Failed to delete secret for {mcp_id}:{key}: {e}")
            return False
    
    @classmethod
    def get_all(cls, mcp_id: str, keys: list[str]) -> dict[str, str]:
        """
        Retrieve multiple secrets for an MCP.
        
        Args:
            mcp_id: The MCP identifier
            keys: List of secret key names to retrieve
            
        Returns:
            Dictionary of key -> value for found secrets
        """
        result = {}
        for key in keys:
            value = cls.get(mcp_id, key)
            if value is not None:
                result[key] = value
        return result
    
    @classmethod
    def delete_all(cls, mcp_id: str, keys: list[str]) -> None:
        """
        Delete all secrets for an MCP.
        
        Args:
            mcp_id: The MCP identifier
            keys: List of secret key names to delete
        """
        for key in keys:
            cls.delete(mcp_id, key)
        logger.info(f"Deleted all secrets for MCP: {mcp_id}")


# Global instance for convenience
secrets_manager = MCPSecretsManager()
