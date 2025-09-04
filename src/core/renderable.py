from dataclasses import dataclass, field
from typing import Optional

from .game_enums import LayerType
from .data_structures import Vector2


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
    position: Vector2
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
    position: Vector2           # Screen/map position
    unit_type: str              # Unit class name for display
    team: int                   # Team ID for color/symbol selection
    hp_current: int             # Current hit points
    hp_max: int                 # Maximum hit points
    facing: str = "south"       # Direction unit is facing
    is_active: bool = True      # Whether unit can currently act
    highlight_type: Optional[str] = None  # Special highlighting (e.g., "target")
    
    # Enhanced stats for strategic TUI
    level: int = 1              # Unit level
    exp: int = 0                # Experience points
    attack: int = 10            # Attack stat
    defense: int = 10           # Defense stat  
    speed: int = 10             # Speed stat
    status_effects: list[str] = field(default_factory=list)  # Active status effects
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UNITS
    
    @property
    def hp_percent(self) -> float:
        """Calculate HP as a percentage (0.0 to 1.0)."""
        return self.hp_current / max(self.hp_max, 1)


@dataclass
class CursorRenderData:
    position: Vector2
    cursor_type: str = "default"
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI


@dataclass
class OverlayTileRenderData:
    position: Vector2
    overlay_type: str
    opacity: float = 0.5
    
    @property
    def layer(self) -> LayerType:
        return LayerType.OVERLAY


@dataclass
class AttackTargetRenderData:
    """Data for rendering attack targeting overlays with AOE support."""
    position: Vector2
    target_type: str  # "range", "aoe", "selected"
    blink_phase: bool = False  # For animation timing
    
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
class BattleForecastRenderData:
    """Battle forecast popup for damage prediction."""
    x: int
    y: int
    width: int = 24
    height: int = 6
    attacker_name: str = ""
    defender_name: str = ""
    damage: int = 0
    hit_chance: int = 0
    crit_chance: int = 0
    can_counter: bool = False
    counter_damage: int = 0
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI


@dataclass
class DialogRenderData:
    """Confirmation dialog with Yes/No options."""
    x: int
    y: int
    width: int
    height: int
    title: str
    message: str
    options: list[str] = field(default_factory=lambda: ["Yes", "No"])
    selected_option: int = 0
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI


@dataclass
class BannerRenderData:
    """Ephemeral banner for phase announcements."""
    x: int
    y: int
    width: int
    text: str
    height: int = 3
    duration_ms: int = 2000  # How long to display
    elapsed_ms: int = 0      # How long it's been shown
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI
    
    @property
    def opacity(self) -> float:
        """Calculate opacity based on elapsed time (fade out effect)."""
        if self.elapsed_ms >= self.duration_ms:
            return 0.0
        fade_start = self.duration_ms * 0.7  # Start fading at 70% of duration
        if self.elapsed_ms < fade_start:
            return 1.0
        fade_progress = (self.elapsed_ms - fade_start) / (self.duration_ms - fade_start)
        return max(0.0, 1.0 - fade_progress)


@dataclass
class OverlayRenderData:
    """Full-screen modal overlay (objectives, help, minimap)."""
    overlay_type: str  # "objectives", "help", "minimap"
    width: int
    height: int
    title: str
    content: list[str] = field(default_factory=list)
    selected_line: int = 0  # For scrollable content
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI
    
    @property
    def x(self) -> int:
        """Center horizontally on screen."""
        return max(0, (80 - self.width) // 2)  # Assume 80-width terminal
    
    @property
    def y(self) -> int:
        """Center vertically on screen."""
        return max(0, (26 - self.height) // 2)  # Assume 26-height terminal


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
    
    # Timer for ephemeral UI elements (milliseconds since start)
    current_time_ms: int = 0
    
    # Cursor position (always present, even when cursor is not visible)
    cursor_x: int = 0
    cursor_y: int = 0
    
    # Existing render data
    tiles: list[TileRenderData] = field(default_factory=list)
    units: list[UnitRenderData] = field(default_factory=list)
    overlays: list[OverlayTileRenderData] = field(default_factory=list)
    attack_targets: list[AttackTargetRenderData] = field(default_factory=list)
    cursor: Optional[CursorRenderData] = None
    menus: list[MenuRenderData] = field(default_factory=list)
    texts: list[TextRenderData] = field(default_factory=list)
    
    # New strategic TUI render data
    battle_forecast: Optional[BattleForecastRenderData] = None
    dialog: Optional[DialogRenderData] = None
    banner: Optional[BannerRenderData] = None
    overlay: Optional[OverlayRenderData] = None
    
