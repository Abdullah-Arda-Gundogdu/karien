"""
MCP Settings UI - Desktop window for managing MCP servers.

Provides a user-friendly interface to:
- View available MCPs from catalog
- Install/uninstall MCPs
- Enable/disable MCPs
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Mock OpenAI Key to bypass config validation (MCP UI doesn't need LLM)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-mcp-ui"

import customtkinter as ctk

from assistant.mcp.manager import mcp_manager
from assistant.mcp.catalog import CatalogEntry
from assistant.mcp.registry import MCPEntry


# Theme configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MCPConfigDialog(ctk.CTkToplevel):
    """Dialog for configuring MCP environment variables."""
    
    def __init__(self, master, mcp_id: str, mcp_name: str, env_schema: dict):
        super().__init__(master)
        
        self.mcp_id = mcp_id
        self.env_schema = env_schema
        self.result = None  # Will be dict of values or None if cancelled
        self._entries = {}
        
        # Window setup
        self.title(f"Configure {mcp_name}")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        # Build UI
        self._build_ui()
        
        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _build_ui(self):
        """Build the dialog UI."""
        # Main container
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(
            self.main_frame,
            text="Configuration Required",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(0, 15))
        
        # Create fields for each env var
        for key, schema in self.env_schema.items():
            frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            
            label_text = schema.get("label", key)
            if schema.get("required"):
                label_text += " *"
            
            ctk.CTkLabel(
                frame,
                text=label_text,
                font=ctk.CTkFont(size=13)
            ).pack(anchor="w")
            
            # Description if available
            if schema.get("description"):
                ctk.CTkLabel(
                    frame,
                    text=schema["description"],
                    font=ctk.CTkFont(size=11),
                    text_color="#6b7280"
                ).pack(anchor="w")
            
            # Entry field (password if secret)
            entry = ctk.CTkEntry(
                frame,
                width=350,
                show="•" if schema.get("secret") else ""
            )
            entry.pack(fill="x", pady=(5, 0))
            self._entries[key] = entry
        
        # Status label for test results
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        self.status_label.pack(anchor="w", pady=(10, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=80,
            fg_color="#4b5563",
            hover_color="#374151",
            command=self._on_cancel
        ).pack(side="left")
        
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Test & Save",
            width=100,
            command=self._on_test_and_save
        )
        self.save_btn.pack(side="right")
    
    def _on_test_and_save(self):
        """Test connection and save if successful."""
        from assistant.mcp.secrets_manager import secrets_manager
        from assistant.mcp.client import MCPClientWrapper
        from assistant.mcp.catalog import MCPCatalog
        from assistant.core.config import config
        
        # Validate required fields
        for key, schema in self.env_schema.items():
            value = self._entries[key].get().strip()
            if schema.get("required") and not value:
                self._entries[key].configure(border_color="#dc2626")
                self.status_label.configure(text="❌ Please fill required fields", text_color="#dc2626")
                return
        
        # Temporarily save to keyring for testing
        env_keys = []
        for key, entry in self._entries.items():
            value = entry.get().strip()
            if value:
                secrets_manager.set(self.mcp_id, key, value)
                env_keys.append(key)
        
        # Test connection
        self.status_label.configure(text="⏳ Testing connection...", text_color="#f59e0b")
        self.update()
        
        async def test_connection():
            catalog = MCPCatalog(config.MCP_CATALOG_PATH)
            catalog_entry = catalog.get(self.mcp_id)
            if not catalog_entry:
                return False, "MCP not found in catalog"
            
            client = MCPClientWrapper(
                self.mcp_id, 
                catalog_entry.command,
                env_keys=env_keys
            )
            try:
                success = await client.connect(timeout=15.0)
                if not success:
                    return False, "Failed to start MCP process"
                
                # Check 1: Tool list found
                if len(client.tools) == 0:
                    await client.disconnect()
                    return False, "No tools found (check logs)"

                # Check 2: Verify Auth if configured
                validation_config = catalog_entry.get_validation_config()
                if validation_config:
                    try:
                        tool_name = validation_config["tool"]
                        tool_args = validation_config.get("args", {})
                        
                        self.status_label.configure(text=f"⏳ Verifying with {tool_name}...", text_color="#f59e0b")
                        self.update()
                        
                        await client.call_tool(tool_name, tool_args)
                    except Exception as e:
                        await client.disconnect()
                        return False, "Authentication failed! Check your token."
                
                await client.disconnect()
                return True, f"Verified! Found {len(client.tools)} tools"
            except Exception as e:
                if client.is_connected:
                    await client.disconnect()
                return False, str(e)
        
        import asyncio
        success, message = asyncio.run(test_connection())
        
        if success:
            self.status_label.configure(text=f"✅ {message}", text_color="#22c55e")
            self.result = {key: entry.get().strip() for key, entry in self._entries.items() if entry.get().strip()}
            self.after(1000, self.destroy)  # Close after 1 second
        else:
            self.status_label.configure(text=f"❌ {message}", text_color="#dc2626")
            # Clean up failed secrets
            for key in env_keys:
                secrets_manager.delete(self.mcp_id, key)
    
    def _on_cancel(self):
        """Cancel configuration."""
        self.result = None
        self.destroy()
    
    def get_result(self) -> dict | None:
        """Wait for dialog and return result."""
        self.wait_window()
        return self.result


class MCPCard(ctk.CTkFrame):
    """Card component displaying a single MCP with actions."""
    
    def __init__(
        self,
        master,
        mcp_id: str,
        name: str,
        description: str,
        is_installed: bool = False,
        is_enabled: bool = False,
        on_install: callable = None,
        on_uninstall: callable = None,
        on_toggle: callable = None,
        **kwargs
    ):
        super().__init__(master, corner_radius=10, **kwargs)
        
        self.mcp_id = mcp_id
        self.is_installed = is_installed
        self.is_enabled = is_enabled
        self.on_install = on_install
        self.on_uninstall = on_uninstall
        self.on_toggle = on_toggle
        
        self.configure(fg_color=("#2b2b2b", "#2b2b2b"))
        
        # Main content
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Header row
        self.header = ctk.CTkFrame(self.content, fg_color="transparent")
        self.header.pack(fill="x")
        
        # Name
        self.name_label = ctk.CTkLabel(
            self.header,
            text=name,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.name_label.pack(side="left")
        
        # Status badge
        if is_installed:
            status_text = "Enabled" if is_enabled else "Disabled"
            status_color = "#22c55e" if is_enabled else "#6b7280"
        else:
            status_text = "Not Installed"
            status_color = "#6b7280"
            
        self.status_badge = ctk.CTkLabel(
            self.header,
            text=status_text,
            font=ctk.CTkFont(size=11),
            fg_color=status_color,
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.status_badge.pack(side="right")
        
        # Description
        self.desc_label = ctk.CTkLabel(
            self.content,
            text=description,
            font=ctk.CTkFont(size=13),
            text_color="#9ca3af",
            anchor="w",
            wraplength=350
        )
        self.desc_label.pack(fill="x", pady=(8, 12))
        
        # Actions
        self.actions = ctk.CTkFrame(self.content, fg_color="transparent")
        self.actions.pack(fill="x")
        
        if is_installed:
            # Toggle switch
            self.toggle_var = ctk.BooleanVar(value=is_enabled)
            self.toggle = ctk.CTkSwitch(
                self.actions,
                text="Enabled",
                variable=self.toggle_var,
                command=self._on_toggle,
                onvalue=True,
                offvalue=False
            )
            self.toggle.pack(side="left")
            
            # Uninstall button
            self.uninstall_btn = ctk.CTkButton(
                self.actions,
                text="Uninstall",
                width=90,
                height=32,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                command=self._on_uninstall
            )
            self.uninstall_btn.pack(side="right")
        else:
            # Install button
            self.install_btn = ctk.CTkButton(
                self.actions,
                text="Install",
                width=90,
                height=32,
                fg_color="#2563eb",
                hover_color="#1d4ed8",
                command=self._on_install
            )
            self.install_btn.pack(side="right")
    
    def _on_install(self):
        if self.on_install:
            self.on_install(self.mcp_id)
    
    def _on_uninstall(self):
        if self.on_uninstall:
            self.on_uninstall(self.mcp_id)
    
    def _on_toggle(self):
        if self.on_toggle:
            self.on_toggle(self.mcp_id, self.toggle_var.get())


class MCPSettingsWindow(ctk.CTk):
    """Main settings window for MCP management."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("MCP Settings")
        self.geometry("500x700")
        self.minsize(450, 500)
        
        # Initialize manager
        mcp_manager._ensure_loaded()
        
        # Build UI
        self._build_ui()
        self._refresh_lists()
    
    def _build_ui(self):
        """Build the main UI layout."""
        # Main container with scrolling
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="MCP Settings",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(anchor="w", pady=(0, 5))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Manage Model Context Protocol servers",
            font=ctk.CTkFont(size=14),
            text_color="#9ca3af"
        )
        self.subtitle_label.pack(anchor="w", pady=(0, 20))
        
        # Installed section
        self.installed_header = ctk.CTkLabel(
            self.main_frame,
            text="Installed",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.installed_header.pack(anchor="w", pady=(10, 10))
        
        self.installed_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.installed_container.pack(fill="x", pady=(0, 20))
        
        # Catalog section
        self.catalog_header = ctk.CTkLabel(
            self.main_frame,
            text="Available",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.catalog_header.pack(anchor="w", pady=(10, 10))
        
        self.catalog_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.catalog_container.pack(fill="x")
    
    def _refresh_lists(self):
        """Refresh both installed and catalog lists."""
        # Clear containers
        for widget in self.installed_container.winfo_children():
            widget.destroy()
        for widget in self.catalog_container.winfo_children():
            widget.destroy()
        
        # Get data
        installed = {mcp.id: mcp for mcp in mcp_manager.get_installed()}
        catalog = mcp_manager.get_available_for_install()
        
        # Installed MCPs
        if installed:
            for mcp in installed.values():
                card = MCPCard(
                    self.installed_container,
                    mcp_id=mcp.id,
                    name=mcp.name,
                    description=mcp.description,
                    is_installed=True,
                    is_enabled=mcp.enabled,
                    on_uninstall=self._handle_uninstall,
                    on_toggle=self._handle_toggle
                )
                card.pack(fill="x", pady=5)
        else:
            no_installed = ctk.CTkLabel(
                self.installed_container,
                text="No MCPs installed yet",
                text_color="#6b7280"
            )
            no_installed.pack(pady=20)
        
        # Catalog MCPs (exclude already installed)
        available = [mcp for mcp in catalog if mcp.id not in installed]
        
        if available:
            for mcp in available:
                card = MCPCard(
                    self.catalog_container,
                    mcp_id=mcp.id,
                    name=mcp.name,
                    description=mcp.description,
                    is_installed=False,
                    on_install=self._handle_install
                )
                card.pack(fill="x", pady=5)
        else:
            all_installed = ctk.CTkLabel(
                self.catalog_container,
                text="All available MCPs are installed",
                text_color="#6b7280"
            )
            all_installed.pack(pady=20)
    
    def _handle_install(self, mcp_id: str):
        """Handle MCP installation."""
        # Check if MCP requires configuration
        catalog_entry = mcp_manager._catalog.get(mcp_id)
        
        if catalog_entry and catalog_entry.requires_config():
            # Show config dialog
            env_schema = catalog_entry.get_env_schema()
            dialog = MCPConfigDialog(self, mcp_id, catalog_entry.name, env_schema)
            result = dialog.get_result()
            
            if result is None:
                # User cancelled
                return
        
        # Proceed with installation
        async def do_install():
            success = await mcp_manager.install_from_catalog(mcp_id)
            if success:
                self._refresh_lists()
        
        asyncio.run(do_install())
    
    def _handle_uninstall(self, mcp_id: str):
        """Handle MCP uninstallation."""
        from assistant.mcp.secrets_manager import secrets_manager
        
        # Clean up secrets from keyring
        catalog_entry = mcp_manager._catalog.get(mcp_id)
        if catalog_entry:
            env_keys = list(catalog_entry.get_env_schema().keys())
            if env_keys:
                secrets_manager.delete_all(mcp_id, env_keys)
        
        async def do_uninstall():
            success = await mcp_manager.uninstall(mcp_id)
            if success:
                self._refresh_lists()
        
        asyncio.run(do_uninstall())
    
    def _handle_toggle(self, mcp_id: str, enabled: bool):
        """Handle MCP enable/disable toggle."""
        async def do_toggle():
            if enabled:
                await mcp_manager.enable(mcp_id)
            else:
                await mcp_manager.disable(mcp_id)
            self._refresh_lists()
        
        asyncio.run(do_toggle())


def main():
    """Launch the MCP Settings window."""
    app = MCPSettingsWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
