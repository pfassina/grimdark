"""
Unit tests for game enumerations.

Tests the various enums used throughout the game engine for
consistency, completeness, and proper behavior.
"""
import pytest
from enum import Enum

from src.core.game_enums import (
    Team, UnitClass, TerrainType
)
from src.core.game_state import GamePhase, BattlePhase
from src.core.game_enums import ObjectiveStatus


class TestTeam:
    """Test the Team enumeration."""
    
    def test_all_teams_exist(self):
        """Test that all expected team values exist."""
        expected_teams = ['PLAYER', 'ENEMY', 'ALLY', 'NEUTRAL']
        actual_teams = [team.name for team in Team]
        
        for expected in expected_teams:
            assert expected in actual_teams
    
    def test_team_values(self):
        """Test team enum values."""
        assert Team.PLAYER.value == 0
        assert Team.ENEMY.value == 1
        assert Team.ALLY.value == 2
        assert Team.NEUTRAL.value == 3
    
    def test_team_string_representation(self):
        """Test team string representation."""
        assert str(Team.PLAYER) == "Team.PLAYER"
        assert str(Team.ENEMY) == "Team.ENEMY"
    
    def test_team_comparison(self):
        """Test team comparison operations."""
        assert Team.PLAYER == Team.PLAYER
        assert Team.PLAYER != Team.ENEMY
        assert Team.ENEMY != Team.ALLY
    
    @pytest.mark.parametrize("team", [Team.PLAYER, Team.ENEMY, Team.ALLY, Team.NEUTRAL])
    def test_team_membership(self, team: Team):
        """Test that all teams are valid Team instances."""
        assert isinstance(team, Team)
        assert team in Team
    
    def test_team_from_value(self):
        """Test creating teams from values."""
        assert Team(0) == Team.PLAYER
        assert Team(1) == Team.ENEMY
        assert Team(2) == Team.ALLY
        assert Team(3) == Team.NEUTRAL
    
    def test_team_iteration(self):
        """Test iterating over all teams."""
        all_teams = list(Team)
        assert len(all_teams) == 4
        assert Team.PLAYER in all_teams
        assert Team.ENEMY in all_teams
        assert Team.ALLY in all_teams
        assert Team.NEUTRAL in all_teams


class TestUnitClass:
    """Test the UnitClass enumeration."""
    
    def test_all_unit_classes_exist(self):
        """Test that all expected unit classes exist."""
        expected_classes = ['KNIGHT', 'ARCHER', 'MAGE', 'WARRIOR', 'PRIEST']
        actual_classes = [unit_class.name for unit_class in UnitClass]
        
        for expected in expected_classes:
            assert expected in actual_classes
    
    def test_unit_class_values(self):
        """Test unit class enum values are consistent."""
        # Values should be distinct
        values = [unit_class.value for unit_class in UnitClass]
        assert len(values) == len(set(values)), "Unit class values should be unique"
    
    @pytest.mark.parametrize("unit_class", [
        UnitClass.KNIGHT, UnitClass.ARCHER, UnitClass.MAGE,
        UnitClass.WARRIOR, UnitClass.PRIEST
    ])
    def test_unit_class_membership(self, unit_class: UnitClass):
        """Test that all unit classes are valid UnitClass instances."""
        assert isinstance(unit_class, UnitClass)
        assert unit_class in UnitClass
    
    def test_unit_class_string_representation(self):
        """Test unit class string representation."""
        assert "KNIGHT" in str(UnitClass.KNIGHT)
        assert "ARCHER" in str(UnitClass.ARCHER)
        assert "MAGE" in str(UnitClass.MAGE)
    
    def test_unit_class_iteration(self):
        """Test iterating over all unit classes."""
        all_classes = list(UnitClass)
        assert len(all_classes) >= 5  # At least the basic classes
        
        # Check that basic classes are present
        assert UnitClass.KNIGHT in all_classes
        assert UnitClass.ARCHER in all_classes
        assert UnitClass.MAGE in all_classes
        assert UnitClass.WARRIOR in all_classes
        assert UnitClass.PRIEST in all_classes


class TestTerrainType:
    """Test the TerrainType enumeration."""
    
    def test_all_terrain_types_exist(self):
        """Test that all expected terrain types exist."""
        expected_types = ['PLAIN', 'FOREST', 'MOUNTAIN', 'WATER']
        actual_types = [terrain.name for terrain in TerrainType]
        
        for expected in expected_types:
            assert expected in actual_types
    
    @pytest.mark.parametrize("terrain", [
        TerrainType.PLAIN, TerrainType.FOREST,
        TerrainType.MOUNTAIN, TerrainType.WATER
    ])
    def test_terrain_type_membership(self, terrain: TerrainType):
        """Test that all terrain types are valid TerrainType instances."""
        assert isinstance(terrain, TerrainType)
        assert terrain in TerrainType
    
    def test_terrain_type_values(self):
        """Test terrain type enum values are consistent."""
        values = [terrain.value for terrain in TerrainType]
        assert len(values) == len(set(values)), "Terrain type values should be unique"
    
    def test_terrain_type_string_representation(self):
        """Test terrain type string representation."""
        assert "PLAIN" in str(TerrainType.PLAIN)
        assert "FOREST" in str(TerrainType.FOREST)
        assert "MOUNTAIN" in str(TerrainType.MOUNTAIN)
        assert "WATER" in str(TerrainType.WATER)
    
    def test_terrain_type_iteration(self):
        """Test iterating over all terrain types."""
        all_types = list(TerrainType)
        assert len(all_types) >= 4  # At least the basic types
        
        assert TerrainType.PLAIN in all_types
        assert TerrainType.FOREST in all_types
        assert TerrainType.MOUNTAIN in all_types
        assert TerrainType.WATER in all_types


class TestObjectiveStatus:
    """Test the ObjectiveStatus enumeration."""
    
    def test_all_objective_statuses_exist(self):
        """Test that all expected objective statuses exist."""
        expected_statuses = ['IN_PROGRESS', 'COMPLETED', 'FAILED']
        actual_statuses = [status.name for status in ObjectiveStatus]
        
        for expected in expected_statuses:
            assert expected in actual_statuses
    
    @pytest.mark.parametrize("status", [
        ObjectiveStatus.IN_PROGRESS,
        ObjectiveStatus.COMPLETED,
        ObjectiveStatus.FAILED
    ])
    def test_objective_status_membership(self, status: ObjectiveStatus):
        """Test that all objective statuses are valid ObjectiveStatus instances."""
        assert isinstance(status, ObjectiveStatus)
        assert status in ObjectiveStatus
    
    def test_objective_status_values(self):
        """Test objective status enum values are consistent."""
        # Values should be distinct integers (auto() generates these)
        values = [status.value for status in ObjectiveStatus]
        assert len(values) == len(set(values)), "ObjectiveStatus values should be unique"
        assert all(isinstance(v, int) for v in values), "ObjectiveStatus values should be integers"
    
    def test_objective_status_string_representation(self):
        """Test objective status string representation."""
        assert "IN_PROGRESS" in str(ObjectiveStatus.IN_PROGRESS)
        assert "COMPLETED" in str(ObjectiveStatus.COMPLETED)
        assert "FAILED" in str(ObjectiveStatus.FAILED)


class TestGamePhase:
    """Test the GamePhase enumeration."""
    
    def test_all_game_phases_exist(self):
        """Test that all expected game phases exist."""
        expected_phases = ['MAIN_MENU', 'BATTLE', 'CUTSCENE', 'GAME_OVER']
        actual_phases = [phase.name for phase in GamePhase]
        
        for expected in expected_phases:
            assert expected in actual_phases
    
    @pytest.mark.parametrize("phase", [
        GamePhase.MAIN_MENU, GamePhase.BATTLE,
        GamePhase.CUTSCENE, GamePhase.GAME_OVER
    ])
    def test_game_phase_membership(self, phase: GamePhase):
        """Test that all game phases are valid GamePhase instances."""
        assert isinstance(phase, GamePhase)
        assert phase in GamePhase
    
    def test_game_phase_values(self):
        """Test game phase enum values are consistent."""
        values = [phase.value for phase in GamePhase]
        assert len(values) == len(set(values)), "Game phase values should be unique"
    
    def test_game_phase_string_representation(self):
        """Test game phase string representation."""
        assert "MAIN_MENU" in str(GamePhase.MAIN_MENU)
        assert "BATTLE" in str(GamePhase.BATTLE)
        assert "GAME_OVER" in str(GamePhase.GAME_OVER)


class TestBattlePhase:
    """Test the BattlePhase enumeration."""
    
    def test_all_battle_phases_exist(self):
        """Test that all expected battle phases exist."""
        expected_phases = ['UNIT_SELECTION', 'UNIT_MOVING', 'TARGETING', 'ENEMY_TURN']
        actual_phases = [phase.name for phase in BattlePhase]
        
        for expected in expected_phases:
            assert expected in actual_phases
    
    @pytest.mark.parametrize("phase", [
        BattlePhase.UNIT_SELECTION, BattlePhase.UNIT_MOVING,
        BattlePhase.TARGETING, BattlePhase.ENEMY_TURN
    ])
    def test_battle_phase_membership(self, phase: BattlePhase):
        """Test that all battle phases are valid BattlePhase instances."""
        assert isinstance(phase, BattlePhase)
        assert phase in BattlePhase
    
    def test_battle_phase_values(self):
        """Test battle phase enum values are consistent."""
        values = [phase.value for phase in BattlePhase]
        assert len(values) == len(set(values)), "Battle phase values should be unique"
    
    def test_battle_phase_string_representation(self):
        """Test battle phase string representation."""
        assert "UNIT_SELECTION" in str(BattlePhase.UNIT_SELECTION)
        assert "UNIT_MOVING" in str(BattlePhase.UNIT_MOVING)
        assert "TARGETING" in str(BattlePhase.TARGETING)
        assert "ENEMY_TURN" in str(BattlePhase.ENEMY_TURN)


class TestEnumIntegration:
    """Test integration between different enums."""
    
    def test_enum_types_are_distinct(self):
        """Test that enum types don't conflict with each other."""
        # These should be different types
        assert type(Team.PLAYER) is not type(UnitClass.KNIGHT)
        assert type(TerrainType.PLAIN) is not type(ObjectiveStatus.IN_PROGRESS)
        assert type(GamePhase.BATTLE) is not type(BattlePhase.UNIT_SELECTION)
    
    def test_enum_inheritance(self):
        """Test that all enums properly inherit from Enum."""
        assert issubclass(Team, Enum)
        assert issubclass(UnitClass, Enum)
        assert issubclass(TerrainType, Enum)
        assert issubclass(ObjectiveStatus, Enum)
        assert issubclass(GamePhase, Enum)
        assert issubclass(BattlePhase, Enum)
    
    def test_enum_values_dont_conflict(self):
        """Test that enum values don't accidentally conflict."""
        # Collect all string values from enums that use strings
        string_values = []
        
        for status in ObjectiveStatus:
            if isinstance(status.value, str):
                string_values.append(status.value)
        
        # Should be no duplicates in string values
        assert len(string_values) == len(set(string_values))
    
    def test_enum_completeness(self):
        """Test that enums have reasonable completeness."""
        # Each enum should have at least 2 values (otherwise why use an enum?)
        assert len(list(Team)) >= 2
        assert len(list(UnitClass)) >= 2
        assert len(list(TerrainType)) >= 2
        assert len(list(ObjectiveStatus)) >= 2
        assert len(list(GamePhase)) >= 2
        assert len(list(BattlePhase)) >= 2
    
    def test_no_enum_name_conflicts(self):
        """Test that enum member names don't conflict across enums."""
        # Collect all member names
        all_names = []
        
        for enum_class in [Team, UnitClass, TerrainType, ObjectiveStatus, GamePhase, BattlePhase]:
            for member in enum_class:
                all_names.append(f"{enum_class.__name__}.{member.name}")
        
        # All names should be unique when qualified
        assert len(all_names) == len(set(all_names))