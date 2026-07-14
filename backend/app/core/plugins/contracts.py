from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import APIRouter


@dataclass(frozen=True)
class PluginManifest:
    name: str
    display_name: str
    version: str
    description: str
    enabled: bool = True
    routes: list[APIRouter] = field(default_factory=list)
    menu_items: list[dict[str, str]] = field(default_factory=list)
    startup_hooks: list[Callable[[], None]] = field(default_factory=list)

