from app.core.plugins.contracts import PluginManifest
from app.plugins.docker.interfaces.router import router

docker_plugin = PluginManifest(
    name="docker",
    display_name="Docker",
    version="0.1.0",
    description="Read-only Docker container, image, volume, and engine monitoring.",
    routes=[router],
    menu_items=[{"name": "docker", "label": "Docker", "path": "/docker"}],
)
