from typing import Optional
from collections import defaultdict

from ..core.renderer import Renderer, RendererConfig
from ..core.entities.renderable import (
    RenderContext, TileRenderData, UnitRenderData, 
    CursorRenderData, OverlayTileRenderData, LayerType
)
from ..core.input import InputEvent, Key
from ..core.tileset_loader import get_tileset_config


class SimpleRenderer(Renderer):
    
    def __init__(self, config: Optional[RendererConfig] = None, demo_mode: bool = True):
        super().__init__(config)
        self._frame_count = 0
        self._auto_quit_at = 10
        self._demo_mode = demo_mode  # Enable/disable auto input simulation
        # Load tileset configuration for gameplay data only
        self.tileset_config = get_tileset_config()
        
        # Simple renderer uses ASCII symbols (maximum compatibility)
        self.terrain_symbols = {
            "plain": ".",
            "forest": "T",      # Tree
            "mountain": "^",    # Caret
            "water": "~",       # Tilde
            "road": "=",
            "fort": "#",        # Hash
            "bridge": "+",      # Plus
            "wall": "#"         # Hash
        }
        
        # Simple renderer UI symbols (ASCII)
        self.ui_symbols = {
            "cursor": "X",
            "movement_overlay": "+",
            "attack_overlay": "*",
            "danger_overlay": "!",
            "highlight_overlay": "o"
        }
        
        # Simple renderer unit symbols (ASCII letters)
        self.unit_symbols = {
            "knight": "K",
            "archer": "A",
            "mage": "M",
            "priest": "P",
            "thief": "T",
            "warrior": "W"
        }
    
    def initialize(self) -> None:
        print(f"Initializing SimpleRenderer ({self.config.width}x{self.config.height})")
        print("=" * self.config.width)
    
    def cleanup(self) -> None:
        print("\nSimpleRenderer cleanup complete")
    
    def clear(self) -> None:
        pass
    
    def present(self) -> None:
        pass
    
    def render_frame(self, context: RenderContext) -> None:
        self._frame_count += 1
        
        print(f"\n--- Frame {self._frame_count} ---")
        
        grid = [[' ' for _ in range(self.config.width)] for _ in range(self.config.height - 3)]
        
        render_items = defaultdict(list)
        
        if context.tiles:
            render_items[LayerType.TERRAIN].extend(context.tiles)
        if context.overlays:
            render_items[LayerType.OVERLAY].extend(context.overlays)
        if context.attack_targets:
            render_items[LayerType.OVERLAY].extend(context.attack_targets)
        if context.units:
            render_items[LayerType.UNITS].extend(context.units)
        if context.cursor:
            render_items[LayerType.UI].append(context.cursor)
        
        for layer in [LayerType.TERRAIN, LayerType.OVERLAY, LayerType.UNITS, LayerType.UI]:
            for item in render_items[layer]:
                self._render_item(item, grid, context)
        
        for row in grid[:20]:
            print(''.join(row[:40]))
        
        if context.texts:
            print("-" * 40)
            for text in context.texts:
                print(text.text[:self.config.width])
    
    def _render_item(self, item, grid, context):
        vx = context.viewport_x
        vy = context.viewport_y
        vw = self.config.width
        vh = self.config.height - 3
        
        screen_x = item.position.x - vx
        screen_y = item.position.y - vy
        
        if 0 <= screen_x < vw and 0 <= screen_y < vh:
            if isinstance(item, TileRenderData):
                # Get ASCII symbol from renderer's own terrain mapping
                symbol = self.terrain_symbols.get(item.terrain_type, "?")
                grid[screen_y][screen_x] = symbol
                    
            elif isinstance(item, OverlayTileRenderData):
                symbol = self.ui_symbols.get(f"{item.overlay_type}_overlay", "?")
                grid[screen_y][screen_x] = symbol
            
            elif hasattr(item, 'target_type'):  # AttackTargetRenderData
                # Simple ASCII representation of targeting
                if item.target_type == "selected":
                    grid[screen_y][screen_x] = "X" if item.blink_phase else "+"
                elif item.target_type == "aoe":
                    grid[screen_y][screen_x] = "*" if item.blink_phase else "+"
                else:  # "range"
                    grid[screen_y][screen_x] = "."
                    
            elif isinstance(item, UnitRenderData):
                symbol = self.unit_symbols.get(item.unit_type.lower(), "?")
                grid[screen_y][screen_x] = symbol
                
            elif isinstance(item, CursorRenderData):
                grid[screen_y][screen_x] = self.ui_symbols["cursor"]
    
    
    def get_input_events(self) -> list[InputEvent]:
        events = []
        
        # Only generate demo input if in demo mode
        if not self._demo_mode:
            return events  # Return empty list for interactive mode
        
        if self._frame_count >= self._auto_quit_at:
            events.append(InputEvent.quit_event())
        elif self._frame_count < 6 and self._frame_count % 2 == 0:
            # First few frames, simulate movement
            print(f"Demo frame {self._frame_count}: Movement simulation")
            movement_keys = [Key.RIGHT, Key.DOWN, Key.LEFT]
            key_index = (self._frame_count // 2) % len(movement_keys)
            events.append(InputEvent.key_press(movement_keys[key_index]))
        elif self._frame_count == 6:
            # Confirm movement position
            print(f"Demo frame {self._frame_count}: Confirming movement position")
            events.append(InputEvent.key_press(Key.ENTER))
        elif self._frame_count == 7:
            # Navigate to Attack action to test attack range display
            print(f"Demo frame {self._frame_count}: Navigate to Attack action")
            events.append(InputEvent.key_press(Key.DOWN))  # Go to Attack
        elif self._frame_count == 8:
            # Select Attack action to test attack range
            print(f"Demo frame {self._frame_count}: Selecting Attack action")
            events.append(InputEvent.key_press(Key.ENTER))
        elif self._frame_count % 3 == 0:
            # Continue with movement
            events.append(InputEvent.key_press(Key.RIGHT))
        
        return events