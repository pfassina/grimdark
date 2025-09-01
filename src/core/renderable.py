from dataclasses import dataclass, field
from typing import Optional

from .game_enums import LayerType


@dataclass
class Color:
    r: int
    g: int
    b: int
    a: int = 255

    @classmethod
    def from_name(cls, name: str) -> "Color":
        colors = {
            "red": cls(255, 0, 0),
            "green": cls(0, 255, 0),
            "blue": cls(0, 0, 255),
            "white": cls(255, 255, 255),
            "black": cls(0, 0, 0),
            "yellow": cls(255, 255, 0),
            "cyan": cls(0, 255, 255),
            "magenta": cls(255, 0, 255),
            "gray": cls(128, 128, 128),
        }
        return colors.get(name, cls(255, 255, 255))


@dataclass
class TileRenderData:
    x: int
    y: int
    terrain_type: str
    elevation: int = 0
    highlight: Optional[str] = None
    
    @property
    def layer(self) -> LayerType:
        return LayerType.TERRAIN


@dataclass
class UnitRenderData:
    """Unit data for rendering and display.
    
    This is the OUTPUT data structure used by renderers to display units.
    It contains only the visual information needed to draw a unit on screen,
    with no game logic or behavior.
    
    Conversion: Unit -> UnitRenderData (via DataConverter.unit_to_render_data)
    """
    x: int                      # Screen/map x-coordinate  
    y: int                      # Screen/map y-coordinate
    unit_type: str              # Unit class name for display
    team: int                   # Team ID for color/symbol selection
    hp_current: int             # Current hit points
    hp_max: int                 # Maximum hit points
    facing: str = "south"       # Direction unit is facing
    is_active: bool = True      # Whether unit can currently act
    highlight_type: Optional[str] = None  # Special highlighting (e.g., "target")
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UNITS
    
    @property
    def hp_percent(self) -> float:
        """Calculate HP as a percentage (0.0 to 1.0)."""
        return self.hp_current / max(self.hp_max, 1)


@dataclass
class CursorRenderData:
    x: int
    y: int
    cursor_type: str = "default"
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI


@dataclass
class OverlayTileRenderData:
    x: int
    y: int
    overlay_type: str
    opacity: float = 0.5
    
    @property
    def layer(self) -> LayerType:
        return LayerType.OVERLAY


@dataclass
class MenuRenderData:
    x: int
    y: int
    width: int
    height: int
    title: str
    items: list[str]
    selected_index: int = 0
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI


@dataclass
class TextRenderData:
    x: int
    y: int
    text: str
    color: Optional[Color] = None
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI


@dataclass
class RenderContext:
    viewport_x: int = 0
    viewport_y: int = 0
    viewport_width: int = 0
    viewport_height: int = 0
    
    world_width: int = 0
    world_height: int = 0
    
    # Game state information
    current_turn: int = 1
    current_team: int = 0
    
    tiles: list[TileRenderData] = field(default_factory=list)
    units: list[UnitRenderData] = field(default_factory=list)
    overlays: list[OverlayTileRenderData] = field(default_factory=list)
    cursor: Optional[CursorRenderData] = None
    menus: list[MenuRenderData] = field(default_factory=list)
    texts: list[TextRenderData] = field(default_factory=list)
    
