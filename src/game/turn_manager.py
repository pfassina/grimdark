"""
Turn management system for handling player and enemy turn flow.

This module manages turn progression, team switching, unit status resets,
and automatic enemy turn processing.
"""
import time
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from .map import GameMap
    from ..core.game_state import GameState

from ..core.events import TurnEnded, TurnStarted
from ..core.game_enums import Team
from ..core.game_state import BattlePhase


class TurnManager:
    """Manages turn progression and team switching."""
    
    def __init__(
        self,
        game_map: "GameMap",
        game_state: "GameState",
        event_emitter: Optional[Callable] = None,
        ui_manager=None
    ):
        self.game_map = game_map
        self.state = game_state
        self.emit_event = event_emitter or (lambda e: None)
        self.ui_manager = ui_manager
        
        # Enemy turn processing timing
        self.enemy_turn_start_time = 0
        self.enemy_turn_duration = 2.0  # 2 seconds per enemy turn
        
        # Callbacks for main game coordination
        self.on_refresh_selectable_units: Optional[Callable] = None
        self.on_position_cursor_on_next_unit: Optional[Callable] = None
        self.on_check_objectives: Optional[Callable] = None
    
    def end_unit_turn(self) -> None:
        """End the current unit's turn and check if team turn should end."""
        self.state.reset_selection()
        self.state.battle_phase = BattlePhase.UNIT_SELECTION
        
        # Refresh selectable units list
        if self.on_refresh_selectable_units:
            self.on_refresh_selectable_units()
        
        # Position cursor on next available player unit
        if self.on_position_cursor_on_next_unit:
            self.on_position_cursor_on_next_unit()
        
        # Check if all player units have finished their actions
        player_units = self.game_map.get_units_by_team(Team.PLAYER)
        if all(not unit.can_move and not unit.can_act for unit in player_units):
            # All player units have finished their actions - start enemy turn
            # Note: Do NOT call unit.end_turn() here, flags should stay set until next turn starts
            self.start_enemy_turn()
        
        # Check objectives after each action
        if self.on_check_objectives:
            self.on_check_objectives()
    
    def start_enemy_turn(self) -> None:
        """Start the enemy team's turn."""
        self.state.start_enemy_turn()
        self.execute_simple_enemy_turn()
    
    def execute_simple_enemy_turn(self) -> None:
        """Execute a simple enemy turn (placeholder AI)."""
        # Emit turn ended event for enemy
        self.emit_turn_ended_event(Team.ENEMY)
        
        # Reset enemy unit statuses for their turn
        for unit in self.game_map.get_units_by_team(Team.ENEMY):
            unit.end_turn()
        
        # Reset player unit statuses for their upcoming turn
        for unit in self.game_map.get_units_by_team(Team.PLAYER):
            unit.start_turn()
        
        # Emit turn started event for player
        self.emit_turn_started_event(Team.PLAYER)
        
        self.state.battle_phase = BattlePhase.UNIT_SELECTION
        
        # Refresh selectable units for new turn
        if self.on_refresh_selectable_units:
            self.on_refresh_selectable_units()
        
        # Position cursor on first available player unit for new turn
        if self.on_position_cursor_on_next_unit:
            self.on_position_cursor_on_next_unit()
        
        # Check objectives at end of turn
        if self.on_check_objectives:
            self.on_check_objectives()
    
    def end_player_turn(self) -> None:
        """End the current player turn and advance to next team."""
        # Store old team info for events
        old_team = self.state.current_team
        old_team_enum = Team(old_team)
        
        # Advance to next team
        self.state.current_team = (self.state.current_team + 1) % 4
        if self.state.current_team == 0:
            self.state.current_turn += 1
        
        # When changing teams, reset unit statuses for the new team
        if self.state.current_team != old_team:
            new_team_enum = Team(self.state.current_team)
            
            # Emit turn ended for old team and turn started for new team
            self.emit_turn_ended_event(old_team_enum)
            self.emit_turn_started_event(new_team_enum)
            
            self.reset_team_unit_statuses(self.state.current_team)
            
            # Show phase banner when changing teams
            self.show_phase_banner(self.state.current_team)
            
            # Start enemy turn timer if switching to non-player team
            if self.state.current_team != 0:
                self.enemy_turn_start_time = time.time()
    
    def reset_team_unit_statuses(self, team: int) -> None:
        """Reset all unit statuses for the specified team at the start of their turn."""
        team_enum = Team(team)
        
        for unit in self.game_map.units.values():
            if unit.team == team_enum and unit.is_alive:
                unit.start_turn()  # Reset has_moved and has_acted flags
    
    def show_phase_banner(self, team: int) -> None:
        """Show phase banner when changing teams."""
        team_names = {
            0: "PLAYER PHASE",
            1: "ENEMY PHASE", 
            2: "ALLY PHASE",
            3: "NEUTRAL PHASE",
        }
        phase_name = team_names.get(team, "UNKNOWN PHASE")
        
        if self.ui_manager:
            self.ui_manager.show_banner(phase_name)
    
    def update_enemy_turn_timing(self) -> None:
        """Handle automatic enemy turn progression."""
        # Only process if it's not the player's turn and we have a start time
        if self.state.current_team != 0 and self.enemy_turn_start_time > 0:
            elapsed_time = time.time() - self.enemy_turn_start_time
            
            # After enemy turn duration, automatically end the enemy turn
            if elapsed_time >= self.enemy_turn_duration:
                # Show end turn message
                team_names = {1: "Enemy", 2: "Ally", 3: "Neutral"}
                team_name = team_names.get(self.state.current_team, "Unknown")
                
                if self.ui_manager:
                    self.ui_manager.show_banner(f"{team_name} Turn Complete")
                
                # Reset timer
                self.enemy_turn_start_time = 0
                
                # End the enemy turn (will cycle to next team/player)
                self.end_player_turn()
    
    def emit_turn_started_event(self, team: Team) -> None:
        """Emit a turn started event."""
        event = TurnStarted(turn=self.state.current_turn, team=team)
        self.emit_event(event)
    
    def emit_turn_ended_event(self, team: Team) -> None:
        """Emit a turn ended event."""
        event = TurnEnded(turn=self.state.current_turn, team=team)
        self.emit_event(event)
    
    def is_player_turn(self) -> bool:
        """Check if it's currently the player's turn."""
        return self.state.current_team == 0
    
    def get_current_team(self) -> Team:
        """Get the current team as an enum."""
        return Team(self.state.current_team)
    
    def get_current_turn(self) -> int:
        """Get the current turn number."""
        return self.state.current_turn