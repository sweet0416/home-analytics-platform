from app.core.plugins.contracts import PluginManifest
from app.shared.exceptions.base import AppError
from app.shared.exceptions.codes import ErrorCode


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}

    def register(self, plugin: PluginManifest) -> None:
        self._plugins[plugin.name] = plugin
        for hook in plugin.startup_hooks:
            hook()

    def shutdown(self) -> None:
        for plugin in reversed(list(self._plugins.values())):
            for hook in plugin.shutdown_hooks:
                hook()

    def list_plugins(self) -> list[PluginManifest]:
        return sorted(self._plugins.values(), key=lambda item: item.name)

    def get_plugin(self, name: str) -> PluginManifest:
        plugin = self._plugins.get(name)
        if plugin is None:
            raise AppError(
                code=ErrorCode.plugin_not_found,
                message=f"Plugin '{name}' was not found.",
                status_code=404,
            )
        return plugin


plugin_registry = PluginRegistry()
