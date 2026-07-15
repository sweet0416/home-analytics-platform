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


def test_plugin_registry_runs_shutdown_hooks_in_reverse_order() -> None:
    calls: list[str] = []
    registry = PluginRegistry()
    registry.register(
        PluginManifest(
            name="first",
            display_name="First",
            version="0.1.0",
            description="First plugin.",
            shutdown_hooks=[lambda: calls.append("first")],
        )
    )
    registry.register(
        PluginManifest(
            name="second",
            display_name="Second",
            version="0.1.0",
            description="Second plugin.",
            shutdown_hooks=[lambda: calls.append("second")],
        )
    )

    registry.shutdown()

    assert calls == ["second", "first"]
