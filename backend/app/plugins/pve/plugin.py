from app.core.plugins.contracts import PluginManifest
from app.plugins.pve.interfaces.router import router

pve_plugin = PluginManifest(
    name="pve",
    display_name="Proxmox VE",
    version="0.1.0",
    description="Read-only Proxmox VE node, guest, storage, and task monitoring.",
    routes=[router],
    menu_items=[{"name": "pve", "label": "PVE", "path": "/pve"}],
)
