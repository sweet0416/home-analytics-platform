from app.core.plugins.contracts import PluginManifest
from app.core.plugins.registry import PluginRegistry


def test_plugin_registry_returns_registered_plugin() -> None:
    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            name="example",
            display_name="Example",
            version="0.1.0",
            description="Example plugin.",
        )
    )

    plugin = registry.get_plugin("example")

    assert plugin.name == "example"
    assert len(registry.list_plugins()) == 1

