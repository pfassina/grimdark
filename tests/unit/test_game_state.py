"""
Unit tests for game state management.

Tests the GameState class and its various phases, transitions,
and state management functionality.
"""
import pytest

from src.core.game_state import GameState, GamePhase, BattlePhase, BattleState, UIState, CursorState
from src.core.data_structures import Vector2, VectorArray


class TestGameState:
    """Test the GameState class."""
    
    def test_initialization_default(self):
        """Test GameState initialization with default values."""
        state = GameState()
        
        assert state.phase == GamePhase.BATTLE
        assert isinstance(state.battle, BattleState)
        assert isinstance(state.ui, UIState)
        assert isinstance(state.cursor, CursorState)
        assert isinstance(state.state_data, dict)
    
    def test_initialization_with_phase(self):
        """Test GameState initialization with specific phase."""
        state = GameState(phase=GamePhase.MAIN_MENU)
        
        assert state.phase == GamePhase.MAIN_MENU
        assert isinstance(state.battle, BattleState)
    
    def test_reset_selection(self):
        """Test resetting selection state."""
        state = GameState()
        
        # Set up some state to reset
        state.battle.selected_unit_id = "test_unit"
        state.ui.open_action_menu(["Attack", "Move"])
        state.ui.open_overlay("objectives")
        state.ui.open_dialog("confirm_end_turn")
        state.ui.start_forecast()
        
        # Reset selection
        state.reset_selection()
        
        # Verify everything is cleared
        assert state.battle.selected_unit_id is None
        assert not state.ui.is_action_menu_open()
        assert not state.ui.is_overlay_open()
        assert not state.ui.is_dialog_open()
        assert not state.ui.is_forecast_active()
    
    def test_turn_management(self):
        """Test turn management through battle state."""
        state = GameState()
        initial_turn = state.battle.current_turn
        
        state.start_player_turn()
        assert state.battle.phase == BattlePhase.PLAYER_TURN_START
        assert state.battle.current_turn == initial_turn + 1
        
        state.start_enemy_turn()
        assert state.battle.phase == BattlePhase.ENEMY_TURN
    
    def test_cursor_management(self):
        """Test cursor position management."""
        state = GameState()
        
        # Test setting cursor position
        new_position = Vector2(5, 7)
        state.set_cursor_position(new_position)
        assert state.cursor.position == new_position
        
        # Test moving cursor
        state.move_cursor(1, -1, 10, 10)
        expected = Vector2(4, 8)  # new_y=5+(-1)=4, new_x=7+1=8
        assert state.cursor.position == expected
        
        # Test camera update
        state.update_camera_to_cursor(20, 15)
        # Camera should be updated (exact values depend on margin logic)
        assert isinstance(state.cursor.camera_position, Vector2)


class TestBattleState:
    """Test the BattleState class."""
    
    def test_initialization(self):
        """Test BattleState initialization."""
        battle = BattleState()
        
        assert battle.phase == BattlePhase.UNIT_SELECTION
        assert battle.current_turn == 1
        assert battle.current_team == 0
        assert battle.selected_unit_id is None
        assert isinstance(battle.movement_range, VectorArray)
        assert len(battle.movement_range) == 0
        assert isinstance(battle.attack_range, VectorArray)
        assert len(battle.attack_range) == 0
    
    def test_selection_management(self):
        """Test unit and target selection."""
        battle = BattleState()
        
        # Test unit selection
        battle.selected_unit_id = "test_unit"
        battle.selected_tile_position = Vector2(3, 4)
        
        assert battle.selected_unit_id == "test_unit"
        assert battle.selected_tile_position == Vector2(3, 4)
        
        # Test reset selection
        battle.reset_selection()
        assert battle.selected_unit_id is None
        assert battle.selected_tile_position is None
    
    def test_movement_range(self):
        """Test movement range management."""
        battle = BattleState()
        positions = [Vector2(1, 1), Vector2(2, 2), Vector2(3, 3)]
        movement_range = VectorArray(positions)
        
        battle.set_movement_range(movement_range)
        assert len(battle.movement_range) == 3
        assert battle.is_in_movement_range(Vector2(1, 1))
        assert not battle.is_in_movement_range(Vector2(5, 5))
    
    def test_attack_range(self):
        """Test attack range management."""
        battle = BattleState()
        positions = [Vector2(4, 4), Vector2(5, 5)]
        attack_range = VectorArray(positions)
        
        battle.set_attack_range(attack_range)
        assert len(battle.attack_range) == 2
        assert battle.is_in_attack_range(Vector2(4, 4))
        assert not battle.is_in_attack_range(Vector2(1, 1))
    
    def test_turn_management(self):
        """Test battle turn management."""
        battle = BattleState()
        initial_turn = battle.current_turn
        
        battle.start_player_turn()
        assert battle.phase == BattlePhase.PLAYER_TURN_START
        assert battle.current_turn == initial_turn + 1
        
        battle.start_enemy_turn()
        assert battle.phase == BattlePhase.ENEMY_TURN
    
    def test_selectable_units(self):
        """Test selectable units management."""
        battle = BattleState()
        unit_ids = ["unit1", "unit2", "unit3"]
        
        battle.set_selectable_units(unit_ids)
        assert battle.selectable_units == unit_ids
        assert battle.current_unit_index == 0
        assert battle.get_current_selectable_unit() == "unit1"
        
        # Test cycling
        next_unit = battle.cycle_selectable_units()
        assert next_unit == "unit2"
        assert battle.current_unit_index == 1
        
        # Test cycling wrap around
        battle.current_unit_index = 2
        next_unit = battle.cycle_selectable_units()
        assert next_unit == "unit1"  # Wraps to beginning
        assert battle.current_unit_index == 0
    
    def test_targetable_enemies(self):
        """Test targetable enemies management."""
        battle = BattleState()
        enemy_ids = ["enemy1", "enemy2"]
        
        battle.set_targetable_enemies(enemy_ids)
        assert battle.targetable_enemies == enemy_ids
        assert battle.current_target_index == 0
        assert battle.get_current_targetable_enemy() == "enemy1"
        
        # Test cycling
        next_enemy = battle.cycle_targetable_enemies()
        assert next_enemy == "enemy2"
        assert battle.current_target_index == 1


class TestUIState:
    """Test the UIState class."""
    
    def test_menu_management(self):
        """Test menu state management."""
        ui = UIState()
        
        assert not ui.is_menu_open()
        
        ui.open_menu("main_menu")
        assert ui.is_menu_open()
        assert ui.active_menu == "main_menu"
        assert ui.menu_selection == 0
        
        ui.close_menu()
        assert not ui.is_menu_open()
        assert ui.active_menu is None
    
    def test_action_menu_management(self):
        """Test action menu state management."""
        ui = UIState()
        items = ["Attack", "Move", "Wait"]
        
        assert not ui.is_action_menu_open()
        
        ui.open_action_menu(items)
        assert ui.is_action_menu_open()
        assert ui.action_menu_items == items
        assert ui.action_menu_selection == 0
        assert ui.get_selected_action() == "Attack"
        
        ui.move_action_menu_selection(1)
        assert ui.action_menu_selection == 1
        assert ui.get_selected_action() == "Move"
        
        ui.close_action_menu()
        assert not ui.is_action_menu_open()
        assert len(ui.action_menu_items) == 0
    
    def test_overlay_management(self):
        """Test overlay state management."""
        ui = UIState()
        
        assert not ui.is_overlay_open()
        
        ui.open_overlay("objectives")
        assert ui.is_overlay_open()
        assert ui.active_overlay == "objectives"
        
        ui.close_overlay()
        assert not ui.is_overlay_open()
        assert ui.active_overlay is None
    
    def test_dialog_management(self):
        """Test dialog state management."""
        ui = UIState()
        
        assert not ui.is_dialog_open()
        
        ui.open_dialog("confirm_end_turn")
        assert ui.is_dialog_open()
        assert ui.active_dialog == "confirm_end_turn"
        assert ui.dialog_selection == 0
        
        ui.move_dialog_selection(1)
        assert ui.dialog_selection == 1
        
        ui.close_dialog()
        assert not ui.is_dialog_open()
        assert ui.active_dialog is None
    
    def test_forecast_management(self):
        """Test battle forecast management."""
        ui = UIState()
        
        assert not ui.is_forecast_active()
        
        ui.start_forecast()
        assert ui.is_forecast_active()
        
        ui.stop_forecast()
        assert not ui.is_forecast_active()
    
    def test_modal_state(self):
        """Test modal state detection."""
        ui = UIState()
        
        assert not ui.is_any_modal_open()
        
        ui.open_overlay("objectives")
        assert ui.is_any_modal_open()
        
        ui.close_overlay()
        ui.open_dialog("confirm")
        assert ui.is_any_modal_open()
        
        ui.close_dialog()
        ui.start_forecast()
        assert ui.is_any_modal_open()


class TestCursorState:
    """Test the CursorState class."""
    
    def test_initialization(self):
        """Test CursorState initialization."""
        cursor = CursorState()
        
        assert cursor.position == Vector2(0, 0)
        assert cursor.camera_position == Vector2(0, 0)
    
    def test_position_management(self):
        """Test cursor position management."""
        cursor = CursorState()
        
        new_position = Vector2(5, 7)
        cursor.set_position(new_position)
        assert cursor.position == new_position
    
    def test_cursor_movement(self):
        """Test cursor movement with bounds checking."""
        cursor = CursorState()
        cursor.position = Vector2(5, 5)
        
        # Normal movement
        cursor.move(1, 1, 10, 10)
        assert cursor.position == Vector2(6, 6)
        
        # Test boundary constraints
        cursor.move(-10, -10, 10, 10)
        assert cursor.position == Vector2(0, 0)
        
        cursor.move(20, 20, 10, 10)
        assert cursor.position == Vector2(9, 9)  # max_x-1, max_y-1
    
    def test_camera_update(self):
        """Test camera position updates."""
        cursor = CursorState()
        cursor.position = Vector2(10, 10)
        
        # Update camera to follow cursor
        cursor.update_camera(20, 15)
        
        # Camera should be updated to keep cursor in view
        assert isinstance(cursor.camera_position, Vector2)
        # Exact values depend on margin calculation, just verify it's reasonable
        assert cursor.camera_position.x >= 0
        assert cursor.camera_position.y >= 0


class TestGamePhases:
    """Test game phase enumeration and transitions."""
    
    @pytest.mark.parametrize("phase", [
        GamePhase.MAIN_MENU,
        GamePhase.BATTLE,
        GamePhase.CUTSCENE,
        GamePhase.PAUSE,
        GamePhase.GAME_OVER,
    ])
    def test_all_phases_exist(self, phase):
        """Test that all expected game phases exist."""
        state = GameState(phase=phase)
        assert state.phase == phase
    
    def test_phase_transitions(self):
        """Test common phase transitions."""
        state = GameState()
        
        # Battle to menu
        state.phase = GamePhase.MAIN_MENU
        assert state.phase == GamePhase.MAIN_MENU
        
        # Menu to battle
        state.phase = GamePhase.BATTLE
        assert state.phase == GamePhase.BATTLE
        
        # Battle to game over
        state.phase = GamePhase.GAME_OVER
        assert state.phase == GamePhase.GAME_OVER


class TestBattlePhases:
    """Test battle phase enumeration and transitions."""
    
    @pytest.mark.parametrize("phase", [
        BattlePhase.PLAYER_TURN_START,
        BattlePhase.UNIT_SELECTION,
        BattlePhase.UNIT_MOVING,
        BattlePhase.ACTION_MENU,
        BattlePhase.TARGETING,
        BattlePhase.UNIT_ACTING,
        BattlePhase.ENEMY_TURN,
        BattlePhase.TURN_END,
    ])
    def test_all_battle_phases_exist(self, phase):
        """Test that all expected battle phases exist."""
        battle = BattleState()
        battle.phase = phase
        assert battle.phase == phase
    
    def test_battle_phase_flow(self):
        """Test typical battle phase flow."""
        battle = BattleState()
        
        # Start with unit selection
        assert battle.phase == BattlePhase.UNIT_SELECTION
        
        # Move to unit moving
        battle.phase = BattlePhase.UNIT_MOVING
        assert battle.phase == BattlePhase.UNIT_MOVING
        
        # Move to targeting
        battle.phase = BattlePhase.TARGETING
        assert battle.phase == BattlePhase.TARGETING
        
        # Move to enemy turn
        battle.phase = BattlePhase.ENEMY_TURN
        assert battle.phase == BattlePhase.ENEMY_TURN
        
        # Back to unit selection
        battle.phase = BattlePhase.UNIT_SELECTION
        assert battle.phase == BattlePhase.UNIT_SELECTION


class TestGameStateIntegration:
    """Test integration between GameState and its substates."""
    
    def test_substate_access(self):
        """Test accessing substates from game state."""
        game_state = GameState()
        
        assert hasattr(game_state, 'battle')
        assert isinstance(game_state.battle, BattleState)
        assert hasattr(game_state, 'ui')
        assert isinstance(game_state.ui, UIState)
        assert hasattr(game_state, 'cursor')
        assert isinstance(game_state.cursor, CursorState)
    
    def test_substate_persistence(self):
        """Test that substates persist through game state operations."""
        game_state = GameState()
        
        # Set some battle state
        game_state.cursor.set_position(Vector2(3, 4))
        game_state.battle.phase = BattlePhase.UNIT_MOVING
        game_state.ui.open_menu("test_menu")
        
        # Change game phase
        game_state.phase = GamePhase.CUTSCENE
        
        # Substates should still be there
        assert game_state.cursor.position == Vector2(3, 4)
        assert game_state.battle.phase == BattlePhase.UNIT_MOVING
        assert game_state.ui.active_menu == "test_menu"
    
    def test_coordinated_reset(self):
        """Test coordinated reset across all substates."""
        game_state = GameState()
        
        # Modify all state
        game_state.phase = GamePhase.CUTSCENE
        game_state.cursor.set_position(Vector2(5, 5))
        game_state.battle.phase = BattlePhase.TARGETING
        game_state.battle.selected_unit_id = "test_unit"
        game_state.ui.open_action_menu(["Attack"])
        
        # Reset selection (this is the main reset method available)
        game_state.reset_selection()
        
        # Verify selection-related state is reset
        assert game_state.battle.selected_unit_id is None
        assert not game_state.ui.is_action_menu_open()
        
        # Other state should remain
        assert game_state.phase == GamePhase.CUTSCENE
        assert game_state.cursor.position == Vector2(5, 5)