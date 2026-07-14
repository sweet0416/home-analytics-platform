from pydantic import BaseModel
from fastapi import APIRouter

from app.core.plugins.registry import plugin_registry
from app.shared.responses.schemas import ApiResponse, ok

router = APIRouter()


class PluginRead(BaseModel):
    name: str
    display_name: str
    version: str
    description: str
    enabled: bool
    menu_items: list[dict[str, str]]


@router.get("", response_model=ApiResponse[list[PluginRead]])
def list_plugins() -> ApiResponse[list[PluginRead]]:
    plugins = [
        PluginRead(
            name=plugin.name,
            display_name=plugin.display_name,
            version=plugin.version,
            description=plugin.description,
            enabled=plugin.enabled,
            menu_items=plugin.menu_items,
        )
        for plugin in plugin_registry.list_plugins()
    ]
    return ok(plugins)


@router.get("/{plugin_name}", response_model=ApiResponse[PluginRead])
def get_plugin(plugin_name: str) -> ApiResponse[PluginRead]:
    plugin = plugin_registry.get_plugin(plugin_name)
    return ok(
        PluginRead(
            name=plugin.name,
            display_name=plugin.display_name,
            version=plugin.version,
            description=plugin.description,
            enabled=plugin.enabled,
            menu_items=plugin.menu_items,
        )
    )

