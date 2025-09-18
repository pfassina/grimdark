"""Entity system foundation.

This package contains the ECS foundation and renderable data structures:
- components.py: Base Component and Entity classes for the ECS system
- renderable.py: Data classes for renderable entities (NO game logic)
"""

from .components import Component, Entity
from .renderable import (
    Color,
    TileRenderData,
    UnitRenderData,
    CursorRenderData,
    BattleForecastRenderData,
    DialogRenderData,
    BannerRenderData,
    OverlayRenderData,
    RenderContext,
)

__all__ = [
    "Component",
    "Entity",
    "Color",
    "TileRenderData",
    "UnitRenderData",
    "CursorRenderData",
    "BattleForecastRenderData",
    "DialogRenderData",
    "BannerRenderData",
    "OverlayRenderData",
    "RenderContext",
]