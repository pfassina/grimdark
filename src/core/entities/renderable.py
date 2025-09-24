from dataclasses import dataclass, field
from typing import Optional

from ..data import LayerType, TerrainType, Vector2


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
    
    # Mana system for spellcasters
    mana_current: int = 0       # Current mana points
    mana_max: int = 0           # Maximum mana points
    
    # Wound and injury information
    wound_count: int = 0                    # Number of active wounds
    wound_descriptions: list[str] = field(default_factory=list)  # Wound descriptions for display
    wound_penalties: dict[str, int] = field(default_factory=dict)  # Stat penalties from wounds
    
    # Morale and psychological state
    morale_current: int = 100              # Current morale level (0-150)
    morale_state: str = "Steady"           # Morale state description
    morale_modifiers: dict[str, int] = field(default_factory=dict)  # Active morale modifiers
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UNITS
    
    @property
    def hp_percent(self) -> float:
        """Calculate HP as a percentage (0.0 to 1.0)."""
        return self.hp_current / max(self.hp_max, 1)
    
    @property
    def mana_percent(self) -> float:
        """Calculate mana as a percentage (0.0 to 1.0)."""
        return self.mana_current / max(self.mana_max, 1) if self.mana_max > 0 else 0.0


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
    overlay_type: str           # "movement", "interrupt_arc", "aoe_preview", "charge_path"
    underlying_terrain: TerrainType  # Terrain type beneath overlay
    terrain_elevation: int           # Elevation of underlying terrain
    opacity: float = 0.5
    
    # Enhanced tactical overlay support
    direction: Optional[str] = None         # For charge paths: "north", "south", "east", "west"
    symbol_override: Optional[str] = None   # Custom symbol for specific overlays (e.g., "→" for paths)
    intensity: int = 1                      # Visual intensity/thickness (for arcs, paths)
    color_hint: Optional[str] = None        # Color suggestion for renderer
    
    @property
    def layer(self) -> LayerType:
        return LayerType.OVERLAY


@dataclass
class AttackTargetRenderData:
    """Data for rendering attack targeting overlays with AOE support."""
    position: Vector2
    target_type: str  # "range", "aoe", "selected", "aoe_preview"  
    blink_phase: bool = False  # For animation timing
    
    # Enhanced targeting display
    preview_intensity: int = 1              # Visual intensity for previews
    is_primary_target: bool = False         # Whether this is the main target of an AoE
    color_hint: Optional[str] = None        # Color suggestion for different target types
    
    @property
    def layer(self) -> LayerType:
        return LayerType.OVERLAY


@dataclass
class ActionMenuItemRenderData:
    """Individual action menu item with enhanced metadata."""
    name: str                           # Action name (e.g., "Fireball")
    action_type: str = "Normal"         # "Light", "Normal", "Heavy", "Prepare"
    weight_cost: int = 100              # Action weight cost (+100, +180, etc.)
    is_available: bool = True           # Whether action can be selected
    description: Optional[str] = None   # Optional detailed description
    icon: str = "⚔"                     # Action icon
    mana_cost: int = 0                  # Mana cost for spells
    
    def format_for_display(self) -> str:
        """Format this action item for display in menu."""
        type_label = f"({self.action_type}, +{self.weight_cost})"
        if self.mana_cost > 0:
            type_label = f"({self.action_type}, +{self.weight_cost}, {self.mana_cost}MP)"
        return f"{self.name} {type_label}"


@dataclass
class MenuRenderData:
    x: int
    y: int
    width: int
    height: int
    title: str
    items: list[str]                    # Legacy string items for compatibility
    selected_index: int = 0
    
    # Enhanced action menu support
    action_items: list[ActionMenuItemRenderData] = field(default_factory=list)  # Enhanced action items
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI
    
    @property 
    def display_items(self) -> list[str]:
        """Get items for display, preferring action_items if available."""
        if self.action_items:
            return [item.format_for_display() for item in self.action_items]
        return self.items


@dataclass
class UnitInfoPanelRenderData:
    """Unit information panel for the 4-panel UI layout."""
    x: int
    y: int
    width: int
    height: int
    
    # Unit identification
    unit_name: str = ""
    unit_class: str = ""
    
    # Core stats
    hp_current: int = 0
    hp_max: int = 0
    mana_current: int = 0
    mana_max: int = 0
    
    # Status and effects
    status_effects: list[str] = field(default_factory=list)  # e.g., ["🔥 Fireball Prep (2 ticks)"]
    wounds: list[str] = field(default_factory=list)          # e.g., ["Burn Scar (-2 max HP)"]
    
    # Action timing
    next_action_ticks: Optional[int] = None  # Ticks until next action
    is_acting_now: bool = False              # Whether unit is currently acting
    
    # Display customization  
    show_mana: bool = True                   # Whether to display mana (for non-casters)
    title: str = "Unit Info"                 # Panel title
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI
    
    @property
    def has_mana(self) -> bool:
        """Check if unit has mana to display."""
        return self.mana_max > 0
    
    def get_hp_display(self) -> str:
        """Format HP for display."""
        return f"HP: {self.hp_current} / {self.hp_max}"
    
    def get_mana_display(self) -> str:
        """Format mana for display."""
        if not self.has_mana:
            return ""
        return f"Mana: {self.mana_current} / {self.mana_max}"
    
    def get_next_action_display(self) -> str:
        """Format next action timing for display."""
        if self.is_acting_now:
            return "Acting Now"
        elif self.next_action_ticks is not None:
            return f"Next Action: in {self.next_action_ticks} ticks"
        else:
            return "Next Action: Unknown"


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
class ActionMenuPanelRenderData:
    """Action menu panel for the 4-panel UI layout."""
    x: int
    y: int
    width: int
    height: int
    
    # Menu content
    title: str = "Actions"
    actions: list[ActionMenuItemRenderData] = field(default_factory=list)
    selected_index: int = 0
    
    # Display customization
    selection_indicator: str = "➤"      # Indicator for selected item
    show_weights: bool = True           # Whether to show action weights
    show_mana_costs: bool = True        # Whether to show mana costs
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI
    
    @property
    def has_actions(self) -> bool:
        """Check if menu has actions to display."""
        return len(self.actions) > 0
    
    def get_selected_action(self) -> Optional[ActionMenuItemRenderData]:
        """Get the currently selected action."""
        if 0 <= self.selected_index < len(self.actions):
            return self.actions[self.selected_index]
        return None
    
    def get_display_lines(self) -> list[str]:
        """Get formatted lines for display."""
        if not self.actions:
            return ["No actions available"]
        
        lines = []
        for i, action in enumerate(self.actions):
            prefix = self.selection_indicator if i == self.selected_index else " "
            formatted_action = action.format_for_display()
            lines.append(f"{prefix} {formatted_action}")
        
        return lines


@dataclass
class LogPanelRenderData:
    """Message log panel for displaying game events and debug information."""
    x: int
    y: int
    width: int
    height: int
    
    # Log messages with formatted text
    messages: list[str] = field(default_factory=list)
    
    # Panel configuration
    title: str = "Message Log"
    show_timestamps: bool = False
    show_categories: bool = True
    
    # Scrolling state
    scroll_offset: int = 0  # How many lines scrolled up from bottom
    total_messages: int = 0  # Total number of messages available
    
    # Category filter state (for future use)
    active_categories: Optional[set[str]] = None
    
    @property
    def layer(self) -> LayerType:
        return LayerType.UI
    
    @property
    def visible_lines(self) -> int:
        """Number of lines that can be displayed in the panel."""
        # Account for title and borders
        return max(0, self.height - 2)
    
    def get_visible_messages(self) -> list[str]:
        """Get the messages that should be visible with current scroll."""
        if not self.messages:
            return ["No messages yet..."]
        
        # If we're not scrolled, show the most recent messages
        if self.scroll_offset == 0:
            return self.messages[-self.visible_lines:]
        
        # Otherwise, show messages from the scroll position
        end_idx = len(self.messages) - self.scroll_offset
        start_idx = max(0, end_idx - self.visible_lines)
        return self.messages[start_idx:end_idx]
    
    def can_scroll_up(self) -> bool:
        """Check if we can scroll up (to older messages)."""
        return self.scroll_offset < len(self.messages) - self.visible_lines
    
    def can_scroll_down(self) -> bool:
        """Check if we can scroll down (to newer messages)."""
        return self.scroll_offset > 0


@dataclass
class BattleForecastRenderData:
    """Battle forecast popup for damage prediction."""
    x: int
    y: int
    width: int = 28  # Increased width to accommodate damage ranges
    height: int = 7  # Increased height for additional info
    attacker_name: str = ""
    defender_name: str = ""
    damage: int = 0
    hit_chance: int = 0
    crit_chance: int = 0
    can_counter: bool = False
    counter_damage: int = 0
    
    # Damage variance information
    min_damage: int = 0
    max_damage: int = 0
    counter_min_damage: int = 0  
    counter_max_damage: int = 0
    
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
class HazardRenderData:
    """Environmental hazard for rendering."""
    position: Vector2
    hazard_type: str  # "fire", "poison_cloud", "collapsing", "ice"
    intensity: int = 1  # Visual intensity/size
    symbol: str = "?"  # Default symbol for rendering
    color_hint: str = "red"  # Color suggestion for renderer
    animation_phase: int = 0  # For animated effects
    warning: bool = False  # If hazard is about to trigger
    
    @property
    def layer(self) -> LayerType:
        return LayerType.OVERLAY  # Hazards render above terrain but below units


@dataclass
class TimelineEntryRenderData:
    """Single timeline entry for display."""
    entity_name: str                    # Unit or entity name
    action_description: str             # What action they're taking
    execution_time: int                 # When they'll act (in ticks)
    relative_time: int                  # Relative time from now (0 = now, 1 = next, etc.)
    entity_type: str = "unit"           # "unit", "hazard", "event"
    team: int = 0                       # Team for color coding
    is_hidden_intent: bool = False      # Whether action is hidden/unknown
    action_weight: int = 100            # Weight of the action
    icon: str = "⚔"                     # Action icon
    
    # Enhanced visibility and timing support
    visibility: str = "full"            # "full", "partial", "hidden" - how much info to show
    ticks_remaining: int = 0            # Ticks until this action executes


@dataclass  
class TimelineRenderData:
    """Timeline visualization for fluid turn-based combat."""
    current_time: int                   # Current timeline tick
    entries: list[TimelineEntryRenderData] = field(default_factory=list)  # Timeline entries to display
    max_entries: int = 8                # Maximum entries to show
    show_weights: bool = True           # Whether to show action weights
    show_times: bool = False            # Whether to show absolute times
    
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
    game_phase: str = "UNKNOWN"
    battle_phase: Optional[str] = None
    
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
    
    # Environmental hazards
    hazards: list[HazardRenderData] = field(default_factory=list)
    
    # Timeline visualization
    timeline: Optional[TimelineRenderData] = None
    
    # New 4-panel UI system
    unit_info_panel: Optional[UnitInfoPanelRenderData] = None
    action_menu_panel: Optional[ActionMenuPanelRenderData] = None
    
    # Message log panel
    log_panel: Optional[LogPanelRenderData] = None
    
