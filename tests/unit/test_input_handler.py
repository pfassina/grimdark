"""
Unit tests for the InputHandler class.

Tests input processing, validation, and routing throughout
the game's input management system.
"""
from unittest.mock import Mock

from src.game.input_handler import InputHandler
from src.core.input import InputEvent, InputType, Key
from src.core.data_structures import Vector2
from src.core.game_state import GameState, GamePhase, BattlePhase
from src.game.map import GameMap


class TestInputHandlerInitialization:
    """Test InputHandler initialization and setup."""
    
    def test_basic_initialization(self):
        """Test InputHandler initialization with basic parameters."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        assert handler.game_map == game_map
        assert handler.state == game_state
        assert handler.renderer == mock_renderer
        assert handler.combat_manager is None
        assert handler.ui_manager is None
    
    def test_initialization_with_managers(self):
        """Test InputHandler initialization with manager dependencies."""
        game_map = GameMap(5, 5)
        game_state = GameState()
        mock_renderer = Mock()
        mock_combat_manager = Mock()
        mock_ui_manager = Mock()
        mock_scenario_menu = Mock()
        
        handler = InputHandler(
            game_map,
            game_state,
            mock_renderer,
            combat_manager=mock_combat_manager,
            ui_manager=mock_ui_manager,
            scenario_menu=mock_scenario_menu
        )
        
        assert handler.combat_manager == mock_combat_manager
        assert handler.ui_manager == mock_ui_manager
        assert handler.scenario_menu == mock_scenario_menu
    
    def test_callback_initialization(self):
        """Test that callbacks are initialized to None."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        assert handler.on_quit is None
        assert handler.on_end_unit_turn is None
        assert handler.on_load_selected_scenario is None
        assert handler.on_movement_preview_update is None


class TestBasicInputHandling:
    """Test basic input event processing."""
    
    def test_handle_empty_event_list(self):
        """Test handling empty event list."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Should not raise any errors
        handler.handle_input_events([])
    
    def test_quit_input_with_callback(self):
        """Test quit input event with callback."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Set up quit callback
        quit_callback = Mock()
        handler.on_quit = quit_callback
        
        # Create quit event
        quit_event = InputEvent(InputType.QUIT)
        
        handler.handle_input_events([quit_event])
        
        quit_callback.assert_called_once()
    
    def test_quit_input_without_callback(self):
        """Test quit input event without callback."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # No quit callback set
        quit_event = InputEvent(InputType.QUIT)
        
        # Should not raise errors even without callback
        handler.handle_input_events([quit_event])
    
    def test_cursor_movement_right(self):
        """Test cursor movement right."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Get initial cursor position
        initial_position = game_state.cursor.position
        
        # Create right key event
        right_event = InputEvent(InputType.KEY_PRESS, key=Key.RIGHT)
        
        handler.handle_input_events([right_event])
        
        # Cursor should have moved right (x coordinate increased)
        new_position = game_state.cursor.position
        assert new_position.x == initial_position.x + 1
        assert new_position.y == initial_position.y  # y should be unchanged
    
    def test_cursor_movement_left(self):
        """Test cursor movement left."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Start cursor at position (0, 5) so we can move left
        game_state.cursor.position = Vector2(0, 5)
        initial_position = game_state.cursor.position
        
        # Create left key event
        left_event = InputEvent(InputType.KEY_PRESS, key=Key.LEFT)
        
        handler.handle_input_events([left_event])
        
        # Cursor should have moved left (x coordinate decreased)
        new_position = game_state.cursor.position
        assert new_position.x == initial_position.x - 1
        assert new_position.y == initial_position.y
    
    def test_cursor_movement_up(self):
        """Test cursor movement up."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Start cursor at position (5, 0) so we can move up
        game_state.cursor.position = Vector2(5, 0)
        initial_position = game_state.cursor.position
        
        # Create up key event
        up_event = InputEvent(InputType.KEY_PRESS, key=Key.UP)
        
        handler.handle_input_events([up_event])
        
        # Cursor should have moved up (y coordinate decreased)
        new_position = game_state.cursor.position
        assert new_position.y == initial_position.y - 1
        assert new_position.x == initial_position.x
    
    def test_cursor_movement_down(self):
        """Test cursor movement down."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Get initial cursor position
        initial_position = game_state.cursor.position
        
        # Create down key event  
        down_event = InputEvent(InputType.KEY_PRESS, key=Key.DOWN)
        
        handler.handle_input_events([down_event])
        
        # Cursor should have moved down (y coordinate increased)
        new_position = game_state.cursor.position
        assert new_position.y == initial_position.y + 1
        assert new_position.x == initial_position.x
    
    def test_cursor_boundary_checking(self):
        """Test cursor movement respects map boundaries."""
        game_map = GameMap(5, 5)  # Small map
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Move cursor to top-left corner
        game_state.cursor.position = Vector2(0, 0)
        
        # Try to move up and left (should be blocked by boundaries)
        up_event = InputEvent(InputType.KEY_PRESS, key=Key.UP)
        left_event = InputEvent(InputType.KEY_PRESS, key=Key.LEFT)
        
        handler.handle_input_events([up_event, left_event])
        
        # Should still be at (0, 0)
        assert game_state.cursor.position == Vector2(0, 0)
        
        # Move cursor to bottom-right corner
        game_state.cursor.position = Vector2(4, 4)
        
        # Try to move down and right (should be blocked)
        down_event = InputEvent(InputType.KEY_PRESS, key=Key.DOWN)
        right_event = InputEvent(InputType.KEY_PRESS, key=Key.RIGHT)
        
        handler.handle_input_events([down_event, right_event])
        
        # Should still be at (4, 4)
        assert game_state.cursor.position == Vector2(4, 4)


class TestActionInputs:
    """Test action-based input handling."""
    
    def test_enter_key_handling(self):
        """Test Enter key processing."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Create Enter key event
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)
        
        # Should process without error
        handler.handle_input_events([enter_event])
    
    def test_escape_key_handling(self):
        """Test Escape key processing."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Create Escape key event
        escape_event = InputEvent(InputType.KEY_PRESS, key=Key.ESCAPE)
        
        # Should process without error
        handler.handle_input_events([escape_event])
    
    def test_space_key_handling(self):
        """Test Space key processing."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Create Space key event
        space_event = InputEvent(InputType.KEY_PRESS, key=Key.SPACE)
        
        # Should process without error
        handler.handle_input_events([space_event])


class TestGamePhaseHandling:
    """Test input handling in different game phases."""
    
    def test_main_menu_phase_input(self):
        """Test input handling in main menu phase."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.MAIN_MENU)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Test navigation in main menu
        down_event = InputEvent(InputType.KEY_PRESS, key=Key.DOWN)
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)
        
        # Should process without error
        handler.handle_input_events([down_event, enter_event])
    
    def test_battle_phase_input(self):
        """Test input handling in battle phase."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Test cursor movement in battle
        right_event = InputEvent(InputType.KEY_PRESS, key=Key.RIGHT)
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)
        
        # Should process without error
        handler.handle_input_events([right_event, enter_event])
    
    def test_cutscene_phase_input(self):
        """Test input handling in cutscene phase."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.CUTSCENE)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Test limited input during cutscene
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)
        escape_event = InputEvent(InputType.KEY_PRESS, key=Key.ESCAPE)
        
        # Should process without error
        handler.handle_input_events([enter_event, escape_event])


class TestBattlePhaseSpecificInput:
    """Test input handling in specific battle phases."""
    
    def test_unit_selection_phase(self):
        """Test input handling in unit selection phase."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        game_state.battle.phase = BattlePhase.UNIT_SELECTION
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Test unit selection inputs
        tab_event = InputEvent(InputType.KEY_PRESS, key=Key.TAB)  # Cycle units
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)  # Select unit
        
        # Should process without error
        handler.handle_input_events([tab_event, enter_event])
    
    def test_targeting_phase(self):
        """Test input handling in targeting phase."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        game_state.battle.phase = BattlePhase.TARGETING
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Test targeting inputs
        right_event = InputEvent(InputType.KEY_PRESS, key=Key.RIGHT)  # Move targeting cursor
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)  # Confirm target
        escape_event = InputEvent(InputType.KEY_PRESS, key=Key.ESCAPE)  # Cancel targeting
        
        # Should process without error
        handler.handle_input_events([right_event, enter_event, escape_event])
    
    def test_enemy_turn_phase(self):
        """Test input handling during enemy turn."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        game_state.battle.phase = BattlePhase.ENEMY_TURN
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # During enemy turn, most inputs should be ignored or limited
        right_event = InputEvent(InputType.KEY_PRESS, key=Key.RIGHT)
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)
        
        # Should process without error (but may not do anything)
        handler.handle_input_events([right_event, enter_event])


class TestInputSequences:
    """Test complex input sequences and workflows."""
    
    def test_movement_sequence(self):
        """Test a sequence of cursor movements."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Start at origin
        initial_position = Vector2(0, 0)
        game_state.cursor.position = initial_position
        
        # Move right, down, left, up
        events = [
            InputEvent(InputType.KEY_PRESS, key=Key.RIGHT),
            InputEvent(InputType.KEY_PRESS, key=Key.DOWN),
            InputEvent(InputType.KEY_PRESS, key=Key.LEFT),
            InputEvent(InputType.KEY_PRESS, key=Key.UP)
        ]
        
        handler.handle_input_events(events)
        
        # Should end up back at origin
        assert game_state.cursor.position == initial_position
    
    def test_mixed_input_sequence(self):
        """Test mixed input types in sequence."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Mixed sequence: movement, action, movement, action
        events = [
            InputEvent(InputType.KEY_PRESS, key=Key.RIGHT),
            InputEvent(InputType.KEY_PRESS, key=Key.ENTER),
            InputEvent(InputType.KEY_PRESS, key=Key.DOWN),
            InputEvent(InputType.KEY_PRESS, key=Key.ESCAPE),
            InputEvent(InputType.KEY_PRESS, key=Key.SPACE)
        ]
        
        # Should process all events without error
        handler.handle_input_events(events)


class TestInputHandlerIntegration:
    """Test InputHandler integration with other systems."""
    
    def test_combat_manager_integration(self):
        """Test InputHandler working with combat manager."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        mock_combat_manager = Mock()
        
        handler = InputHandler(
            game_map,
            game_state,
            mock_renderer,
            combat_manager=mock_combat_manager
        )
        
        # Test inputs that might interact with combat manager
        enter_event = InputEvent(InputType.KEY_PRESS, key=Key.ENTER)
        
        # Should process without error
        handler.handle_input_events([enter_event])
    
    def test_ui_manager_integration(self):
        """Test InputHandler working with UI manager."""
        game_map = GameMap(10, 10)
        game_state = GameState(phase=GamePhase.BATTLE)
        mock_renderer = Mock()
        mock_ui_manager = Mock()
        
        handler = InputHandler(
            game_map,
            game_state,
            mock_renderer,
            ui_manager=mock_ui_manager
        )
        
        # Test inputs that might interact with UI manager
        escape_event = InputEvent(InputType.KEY_PRESS, key=Key.ESCAPE)
        
        # Should process without error
        handler.handle_input_events([escape_event])
    
    def test_callback_integration(self):
        """Test InputHandler callback system."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Set up callbacks
        mock_quit_callback = Mock()
        mock_end_turn_callback = Mock()
        mock_movement_callback = Mock()
        
        handler.on_quit = mock_quit_callback
        handler.on_end_unit_turn = mock_end_turn_callback
        handler.on_movement_preview_update = mock_movement_callback
        
        # Test quit callback
        quit_event = InputEvent(InputType.QUIT)
        handler.handle_input_events([quit_event])
        
        mock_quit_callback.assert_called_once()


class TestInputHandlerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_input_type(self):
        """Test handling of unknown input types."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Create event with unknown type (this would be unusual but possible)
        unknown_event = InputEvent(InputType.MOUSE_CLICK)  # Mouse not typically handled
        
        # Should not crash
        handler.handle_input_events([unknown_event])
    
    def test_multiple_events_processing(self):
        """Test processing multiple events in one call."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Create many events
        events = [
            InputEvent(InputType.KEY_PRESS, key=Key.RIGHT),
            InputEvent(InputType.KEY_PRESS, key=Key.DOWN),
            InputEvent(InputType.KEY_PRESS, key=Key.LEFT),
            InputEvent(InputType.KEY_PRESS, key=Key.UP),
            InputEvent(InputType.KEY_PRESS, key=Key.ENTER),
            InputEvent(InputType.KEY_PRESS, key=Key.ESCAPE),
            InputEvent(InputType.KEY_PRESS, key=Key.SPACE),
            InputEvent(InputType.KEY_PRESS, key=Key.TAB)
        ]
        
        # Should handle all events
        handler.handle_input_events(events)
    
    def test_state_modification_during_input(self):
        """Test that input processing can modify game state."""
        game_map = GameMap(10, 10)
        game_state = GameState()
        mock_renderer = Mock()
        
        handler = InputHandler(game_map, game_state, mock_renderer)
        
        # Record initial state
        initial_cursor_pos = game_state.cursor.position
        
        # Send movement input
        right_event = InputEvent(InputType.KEY_PRESS, key=Key.RIGHT)
        handler.handle_input_events([right_event])
        
        # State should have been modified
        assert game_state.cursor.position != initial_cursor_pos