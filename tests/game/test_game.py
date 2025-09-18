"""
Unit tests for the Game orchestrator class.

Tests the main game coordination functionality, manager initialization,
event system setup, and game loop mechanics.
"""

import pytest
from unittest.mock import Mock, patch

from src.game.game import Game
from src.core.engine.game_state import GameState, GamePhase, BattlePhase
from src.core.events.event_manager import EventManager
from src.core.events.events import GameEnded, LogMessage
from src.core.input import InputEvent


class MockRenderer:
    """Mock renderer for testing Game class."""
    
    def __init__(self):
        self.started = False
        self.stopped = False
        self.cleared = False
        self.presented = False
        
    def start(self):
        self.started = True
        
    def stop(self):
        self.stopped = True
        
    def clear(self):
        self.cleared = True
        
    def present(self):
        self.presented = True
        
    def render_frame(self, context):
        pass
        
    def get_input_events(self):
        return []


class MockGameMap:
    """Mock game map for testing."""
    
    def __init__(self):
        self.width = 10
        self.height = 10
        self.units = []


class MockScenario:
    """Mock scenario for testing."""
    
    def __init__(self, name="Test Scenario"):
        self.name = name
        self.filepath = "test_scenario.yaml"


class TestGameInitialization:
    """Test Game class initialization and setup."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_scenario(self):
        return MockScenario()
    
    def test_game_creation_minimal(self, mock_renderer):
        """Test basic game creation with minimal parameters."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        assert game.renderer == mock_renderer
        assert isinstance(game.state, GameState)
        assert game.state.phase == GamePhase.MAIN_MENU
        assert game.game_map is None
        assert game.scenario is None
        assert not game.running
        assert game.fps == 30
        assert isinstance(game.event_manager, EventManager)
        
    def test_game_creation_with_scenario(self, mock_renderer, mock_game_map, mock_scenario):
        """Test game creation with scenario and map."""
        game = Game(
            game_map=mock_game_map,
            renderer=mock_renderer,
            scenario=mock_scenario
        )
        
        assert game.game_map == mock_game_map
        assert game.scenario == mock_scenario
        assert game.scenario is not None
        assert game.scenario.name == "Test Scenario"
        
    def test_manager_properties_before_initialization(self, mock_renderer):
        """Test that manager properties raise errors before initialization."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        with pytest.raises(RuntimeError, match="LogManager not initialized"):
            _ = game.log_manager
            
        with pytest.raises(RuntimeError, match="PhaseManager not initialized"):
            _ = game.phase_manager
            
        with pytest.raises(RuntimeError, match="UIManager not initialized"):
            _ = game.ui_manager
            
        with pytest.raises(RuntimeError, match="CombatManager not initialized"):
            _ = game.combat_manager
            
    def test_ensure_game_map_error(self, mock_renderer):
        """Test that _ensure_game_map raises error when map is None."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        with pytest.raises(RuntimeError, match="Game map not initialized"):
            game._ensure_game_map()


class TestGameManagerInitialization:
    """Test Game manager initialization process."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_scenario(self):
        return MockScenario()
    
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    def test_setup_event_system(self, mock_scenario_mgr, mock_render_builder,
                                mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                mock_renderer):
        """Test event system setup."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        game._setup_event_system()
        
        # LogManager should be created with event manager and state
        mock_log_mgr.assert_called_once_with(
            event_manager=game.event_manager,
            game_state=game.state
        )
        
        # PhaseManager should be created
        mock_phase_mgr.assert_called_once_with(
            game_state=game.state,
            event_manager=game.event_manager
        )
        
        # Verify managers are set
        assert game._log_manager is not None
        assert game._phase_manager is not None
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    def test_initialize_managers_without_map(self, mock_scenario_mgr, mock_render_builder,
                                           mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                           mock_renderer):
        """Test manager initialization without game map."""
        game = Game(game_map=None, renderer=mock_renderer)
        game._setup_event_system()
        
        game._initialize_managers()
        
        # Basic managers should be initialized
        mock_input_handler.assert_called_once()
        mock_render_builder.assert_called_once()
        mock_scenario_mgr.assert_called_once()
        
        # Map-dependent managers should not be initialized
        assert game._ui_manager is None
        assert game._combat_manager is None
        assert game._timeline_manager is None
        assert game._selection_manager is None
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    @patch('src.game.game.UIManager')
    @patch('src.game.game.SelectionManager')
    @patch('src.game.game.CombatManager')
    @patch('src.game.game.TimelineManager')
    def test_initialize_managers_with_map(self, mock_timeline_mgr, mock_combat_mgr,
                                         mock_selection_mgr, mock_ui_mgr,
                                         mock_scenario_mgr, mock_render_builder,
                                         mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                         mock_renderer, mock_game_map, mock_scenario):
        """Test manager initialization with game map."""
        game = Game(game_map=mock_game_map, renderer=mock_renderer, scenario=mock_scenario)
        game._setup_event_system()
        
        game._initialize_managers()
        
        # All managers should be initialized
        mock_input_handler.assert_called_once()
        mock_render_builder.assert_called_once()
        mock_scenario_mgr.assert_called_once()
        mock_ui_mgr.assert_called_once()
        mock_selection_mgr.assert_called_once()
        mock_combat_mgr.assert_called_once()
        mock_timeline_mgr.assert_called_once()
        
        # Verify map-dependent managers get the map
        ui_call_args = mock_ui_mgr.call_args[1]
        assert ui_call_args['game_map'] == mock_game_map
        assert ui_call_args['scenario'] == mock_scenario
        
    def test_manager_properties_after_initialization(self, mock_renderer, mock_game_map):
        """Test that manager properties work after initialization."""
        with patch('src.game.game.LogManager') as mock_log_mgr, \
             patch('src.game.game.PhaseManager') as mock_phase_mgr, \
             patch('src.game.game.InputHandler') as mock_input_handler, \
             patch('src.game.game.RenderBuilder') as mock_render_builder, \
             patch('src.game.game.ScenarioManager') as mock_scenario_mgr, \
             patch('src.game.game.UIManager') as mock_ui_mgr, \
             patch('src.game.game.SelectionManager') as mock_selection_mgr, \
             patch('src.game.game.CombatManager') as mock_combat_mgr, \
             patch('src.game.game.TimelineManager') as mock_timeline_mgr:
            
            game = Game(game_map=mock_game_map, renderer=mock_renderer)
            game._setup_event_system()
            game._initialize_managers()
            
            # Manager properties should return the mocked instances
            assert game.log_manager == mock_log_mgr.return_value
            assert game.phase_manager == mock_phase_mgr.return_value
            assert game.input_handler == mock_input_handler.return_value
            assert game.render_builder == mock_render_builder.return_value
            assert game.scenario_manager == mock_scenario_mgr.return_value
            assert game.ui_manager == mock_ui_mgr.return_value
            assert game.selection_manager == mock_selection_mgr.return_value
            assert game.combat_manager == mock_combat_mgr.return_value
            assert game.timeline_manager == mock_timeline_mgr.return_value


class TestGameInitializeMethod:
    """Test the main initialize() method."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @pytest.fixture
    def mock_scenario(self):
        return MockScenario()
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    def test_initialize_menu_mode(self, mock_scenario_mgr, mock_render_builder,
                                 mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                 mock_renderer):
        """Test initialization in main menu mode."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        # Mock the callback setup to avoid errors
        mock_input_handler.return_value.on_quit = None
        mock_input_handler.return_value.on_load_selected_scenario = None
        
        game.initialize()
        
        assert game.running
        assert mock_renderer.started
        assert game.state.phase == GamePhase.MAIN_MENU
        
        # Should publish GameStarted event
        # Event processing happens during initialization
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    @patch('src.game.game.UIManager')
    @patch('src.game.game.SelectionManager')
    @patch('src.game.game.CombatManager')
    @patch('src.game.game.TimelineManager')
    def test_initialize_battle_mode(self, mock_timeline_mgr, mock_combat_mgr,
                                   mock_selection_mgr, mock_ui_mgr,
                                   mock_scenario_mgr, mock_render_builder,
                                   mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                   mock_renderer, mock_game_map, mock_scenario):
        """Test initialization in battle mode with scenario."""
        game = Game(game_map=mock_game_map, renderer=mock_renderer, scenario=mock_scenario)
        
        # Mock the callback setup
        mock_input_handler.return_value.on_quit = None
        mock_input_handler.return_value.on_load_selected_scenario = None
        mock_timeline_mgr.return_value.initialize_battle_timeline = Mock()
        
        game.initialize()
        
        assert game.running
        assert mock_renderer.started
        
        # Should initialize timeline if in battle phase
        if game.state.phase == GamePhase.BATTLE:
            mock_timeline_mgr.return_value.initialize_battle_timeline.assert_called_once()
            
    def test_initialize_invalid_state_no_map(self, mock_renderer):
        """Test initialization with invalid state - battle phase but no map."""
        game = Game(game_map=None, renderer=mock_renderer)
        game.state.phase = GamePhase.BATTLE  # Invalid: battle phase without map
        
        with pytest.raises(RuntimeError, match="Invalid state.*no game_map exists"):
            game.initialize()


class TestGameEventSystem:
    """Test Game event system integration."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
    
    def test_emit_log(self, mock_renderer):
        """Test log message emission."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        published_events = []
        def capture_event(event, priority=None, source=None):
            published_events.append((event, source))
            
        game.event_manager.publish = capture_event
        
        game._emit_log("Test message", "TEST", "DEBUG")
        
        assert len(published_events) == 1
        event, source = published_events[0]
        assert isinstance(event, LogMessage)
        assert event.message == "Test message"
        assert event.category == "TEST"
        assert event.level == "DEBUG"
        assert source == "Game"


class TestGameLoop:
    """Test Game loop functionality."""
    
    @pytest.fixture
    def mock_renderer(self):
        renderer = MockRenderer()
        renderer.get_input_events = Mock(return_value=[])
        return renderer
        
    @pytest.fixture 
    def mock_game_map(self):
        return MockGameMap()
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    def test_update_main_menu(self, mock_scenario_mgr, mock_render_builder,
                             mock_input_handler, mock_phase_mgr, mock_log_mgr,
                             mock_renderer):
        """Test update loop in main menu phase."""
        game = Game(game_map=None, renderer=mock_renderer)
        game.event_manager.process_events = Mock()
        game.event_manager.has_high_priority_events = Mock(return_value=False)
        
        # Mock input handler methods
        mock_input_handler.return_value.handle_main_menu_input = Mock()
        mock_input_handler.return_value.on_quit = None
        mock_input_handler.return_value.on_load_selected_scenario = None
        
        game.initialize()
        
        # Create a quit input event
        quit_event = InputEvent.quit_event()
        mock_renderer.get_input_events.return_value = [quit_event]
        
        game.update()
        
        # Should handle quit in main menu
        assert not game.running
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager') 
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    @patch('src.game.game.UIManager')
    @patch('src.game.game.SelectionManager')
    @patch('src.game.game.CombatManager')
    @patch('src.game.game.TimelineManager')
    def test_update_battle_timeline_processing(self, mock_timeline_mgr, mock_combat_mgr,
                                              mock_selection_mgr, mock_ui_mgr,
                                              mock_scenario_mgr, mock_render_builder,
                                              mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                              mock_renderer, mock_game_map):
        """Test update loop during battle timeline processing."""
        game = Game(game_map=mock_game_map, renderer=mock_renderer)
        game.state.phase = GamePhase.BATTLE
        game.state.battle.phase = BattlePhase.TIMELINE_PROCESSING
        
        game.event_manager.process_events = Mock()
        game.event_manager.has_high_priority_events = Mock(return_value=False)
        
        # Mock manager methods
        mock_ui_mgr.return_value.update_banner_timing = Mock()
        mock_timeline_mgr.return_value.process_timeline = Mock()
        mock_timeline_mgr.return_value.initialize_battle_timeline = Mock()
        mock_input_handler.return_value.handle_input_events = Mock()
        mock_input_handler.return_value.on_quit = None
        mock_input_handler.return_value.on_load_selected_scenario = None
        
        game.initialize()
        game.update()
        
        # Should update UI timing and process timeline
        mock_ui_mgr.return_value.update_banner_timing.assert_called_once()
        mock_timeline_mgr.return_value.process_timeline.assert_called_once()
        mock_input_handler.return_value.handle_input_events.assert_called_once()
        
    def test_render(self, mock_renderer):
        """Test render method."""
        with patch('src.game.game.LogManager'), \
             patch('src.game.game.PhaseManager'), \
             patch('src.game.game.InputHandler'), \
             patch('src.game.game.RenderBuilder') as mock_render_builder, \
             patch('src.game.game.ScenarioManager'):
            
            game = Game(game_map=None, renderer=mock_renderer)
            
            # Mock render builder
            mock_context = Mock()
            mock_render_builder.return_value.build_render_context.return_value = mock_context
            mock_render_builder.return_value.on_quit = None
            mock_render_builder.return_value.on_load_selected_scenario = None
            
            game.initialize()
            game.render()
            
            # Should build context and render
            mock_render_builder.return_value.build_render_context.assert_called_once()
            assert mock_renderer.cleared
            assert mock_renderer.presented


class TestGameScenarioLoading:
    """Test scenario loading functionality."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    @pytest.fixture
    def mock_scenario(self):
        return MockScenario("Loaded Scenario")
        
    @pytest.fixture
    def mock_game_map(self):
        return MockGameMap()
        
    @patch('src.game.game.LogManager')
    @patch('src.game.game.PhaseManager')
    @patch('src.game.game.InputHandler')
    @patch('src.game.game.RenderBuilder')
    @patch('src.game.game.ScenarioManager')
    @patch('src.game.game.UIManager')
    @patch('src.game.game.SelectionManager')
    @patch('src.game.game.CombatManager')
    @patch('src.game.game.TimelineManager')
    def test_load_selected_scenario(self, mock_timeline_mgr, mock_combat_mgr,
                                   mock_selection_mgr, mock_ui_mgr,
                                   mock_scenario_mgr, mock_render_builder,
                                   mock_input_handler, mock_phase_mgr, mock_log_mgr,
                                   mock_renderer, mock_scenario, mock_game_map):
        """Test loading scenario from menu."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        # Mock scenario manager to return scenario and map
        mock_scenario_mgr.return_value.load_selected_scenario_from_menu.return_value = (
            mock_scenario, mock_game_map
        )
        mock_scenario_mgr.return_value.initialize_objective_system = Mock()
        mock_timeline_mgr.return_value.initialize_battle_timeline = Mock()
        
        # Mock other methods to avoid errors
        mock_input_handler.return_value.on_quit = None
        mock_input_handler.return_value.on_load_selected_scenario = None
        
        game.event_manager.process_events = Mock()
        game.initialize()
        
        # Initially no scenario or map
        assert game.scenario is None
        assert game.game_map is None
        
        game.load_selected_scenario()
        
        # Should update scenario and map
        assert game.scenario == mock_scenario
        assert game.game_map == mock_game_map
        
        # Should initialize systems
        mock_scenario_mgr.return_value.initialize_objective_system.assert_called_once()
        mock_timeline_mgr.return_value.initialize_battle_timeline.assert_called_once()


class TestGameCallbacks:
    """Test Game callback handlers."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    def test_handle_quit(self, mock_renderer):
        """Test quit callback handler."""
        game = Game(game_map=None, renderer=mock_renderer)
        assert game.running is False  # Not running initially
        
        game.running = True  # Simulate running state
        game._handle_quit()
        
        assert not game.running


class TestGameCleanup:
    """Test Game cleanup functionality."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    def test_cleanup(self, mock_renderer):
        """Test game cleanup process."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        # Mock event system
        published_events = []
        def capture_event(event, priority=None, source=None):
            published_events.append((event, source))
            
        game.event_manager.publish = capture_event
        game.event_manager.process_events = Mock()
        game.event_manager.shutdown = Mock()
        
        game.cleanup()
        
        # Should publish GameEnded event
        assert len(published_events) == 1
        event, source = published_events[0]
        assert isinstance(event, GameEnded)
        assert event.result == "quit"
        assert event.reason == "cleanup"
        assert source == "Game"
        
        # Should process events and shutdown
        game.event_manager.process_events.assert_called_once()
        game.event_manager.shutdown.assert_called_once()
        assert mock_renderer.stopped


class TestGameEdgeCases:
    """Test Game edge cases and error conditions."""
    
    @pytest.fixture
    def mock_renderer(self):
        return MockRenderer()
        
    def test_manager_dependency_validation(self, mock_renderer):
        """Test that manager dependencies are properly validated."""
        game = Game(game_map=None, renderer=mock_renderer)
        
        # Test the _require_manager method directly
        with pytest.raises(RuntimeError, match="TestManager not initialized"):
            game._require_manager(None, "TestManager")
            
        # Should return manager if not None
        mock_manager = Mock()
        result = game._require_manager(mock_manager, "TestManager")
        assert result == mock_manager
        
    def test_ensure_game_map_success(self, mock_renderer):
        """Test _ensure_game_map when map exists."""
        mock_map = MockGameMap()
        game = Game(game_map=mock_map, renderer=mock_renderer)  # type: ignore[arg-type]
        
        result = game._ensure_game_map()
        assert result == mock_map