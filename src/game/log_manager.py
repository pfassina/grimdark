"""
Log management system for game messages and debugging.

This module provides centralized logging with categorization, filtering,
and efficient storage for display in the game's UI.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.event_manager import EventManager
    from ..core.game_state import GameState


class LogCategory(Enum):
    """Categories for log messages."""
    SYSTEM = auto()     # System messages (initialization, loading, etc.)
    BATTLE = auto()     # Combat-related messages
    MOVEMENT = auto()   # Unit movement messages
    AI = auto()         # AI decision messages
    TIMELINE = auto()   # Timeline system messages
    INPUT = auto()      # Input handling messages
    DEBUG = auto()      # Debug messages
    WARNING = auto()    # Warning messages
    ERROR = auto()      # Error messages
    OBJECTIVE = auto()  # Objective-related messages
    INTERRUPT = auto()  # Interrupt system messages
    SCENARIO = auto()   # Scenario loading messages
    UI = auto()         # UI-related messages


@dataclass
class LogMessage:
    """A single log message with metadata."""
    text: str
    category: LogCategory
    timestamp: datetime = field(default_factory=datetime.now)
    
    def format(self, include_timestamp: bool = False, include_category: bool = True) -> str:
        """Format the message for display."""
        parts = []
        
        if include_timestamp:
            time_str = self.timestamp.strftime("%H:%M:%S")
            parts.append(f"[{time_str}]")
        
        if include_category:
            # Short category tags for display
            category_tags = {
                LogCategory.SYSTEM: "SYS",
                LogCategory.BATTLE: "BTL",
                LogCategory.MOVEMENT: "MOV",
                LogCategory.AI: "AI",
                LogCategory.TIMELINE: "TML",
                LogCategory.INPUT: "INP",
                LogCategory.DEBUG: "DBG",
                LogCategory.WARNING: "WRN",
                LogCategory.ERROR: "ERR",
                LogCategory.OBJECTIVE: "OBJ",
                LogCategory.INTERRUPT: "INT",
                LogCategory.SCENARIO: "SCN",
                LogCategory.UI: "UI",
            }
            tag = category_tags.get(self.category, "???")
            parts.append(f"[{tag}]")
        
        parts.append(self.text)
        return " ".join(parts)


class LogLevel(Enum):
    """Log levels for filtering."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


class LogManager:
    """Manages game logging with categorization and filtering."""
    
    def __init__(
        self, 
        event_manager: "EventManager",
        game_state: "GameState",
        max_messages: int = 1000, 
        default_level: LogLevel = LogLevel.INFO
    ):
        """Initialize the log manager.
        
        Args:
            event_manager: Event manager for event-driven logging (required)
            game_state: Game state to update with log data (required)
            max_messages: Maximum number of messages to store in the buffer
            default_level: Default log level for filtering
        """
        self.messages: deque[LogMessage] = deque(maxlen=max_messages)
        self.log_level = default_level
        self.enabled_categories = set(LogCategory)  # All categories enabled by default
        self.event_manager = event_manager
        self.game_state = game_state
        
        # Category-specific log level mappings
        self.category_levels = {
            # Debug-only categories (only show when debug is enabled)
            LogCategory.DEBUG: LogLevel.DEBUG,
            LogCategory.INPUT: LogLevel.DEBUG,      # Key presses, input handling
            LogCategory.AI: LogLevel.DEBUG,         # AI decision making
            LogCategory.TIMELINE: LogLevel.DEBUG,   # Timeline system processing
            LogCategory.INTERRUPT: LogLevel.DEBUG,  # Interrupt system details
            
            # Always visible categories
            LogCategory.WARNING: LogLevel.WARNING,
            LogCategory.ERROR: LogLevel.ERROR,
            
            # Normal gameplay categories (INFO level)
            # SYSTEM, BATTLE, MOVEMENT, UI, OBJECTIVE, SCENARIO default to INFO
        }
        
        # Set up event subscriptions (event manager is required)
        self._setup_event_subscriptions()
        
        # Initialize log data in game state (game state is required)
        self._update_game_state_log_data()
    
    def _update_game_state_log_data(self) -> None:
        """Update the game state with current log data for UI access."""
        # Create formatted messages for UI display
        formatted_messages = []
        for msg in self.messages:
            formatted_messages.append(msg.format(include_timestamp=False, include_category=True))
        
        # Update game state with log data (game state is required)
        self.game_state.log_data = {
            'messages': formatted_messages,
            'debug_enabled': self.is_debug_enabled(),
            'total_messages': len(self.messages)
        }
    
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for centralized logging."""
        from ..core.events import EventType
        
        # Subscribe to log message events (event manager is required)
        self.event_manager.subscribe(
            EventType.LOG_MESSAGE,
            self._handle_log_message_event,
            subscriber_name="LogManager.log_message"
        )
        
        # Subscribe to debug message events
        self.event_manager.subscribe(
            EventType.DEBUG_MESSAGE,
            self._handle_debug_message_event,
            subscriber_name="LogManager.debug_message"
        )
        
        # Subscribe to log save requests
        self.event_manager.subscribe(
            EventType.LOG_SAVE_REQUESTED,
            self._handle_log_save_request,
            subscriber_name="LogManager.log_save_request"
        )
    
    def _handle_log_message_event(self, event) -> None:
        """Handle log message events from the event system."""
        from ..core.events import LogMessage as LogEvent
        if isinstance(event, LogEvent):
            # Map event category string to LogCategory enum
            try:
                category = LogCategory[event.category.upper()]
            except (KeyError, AttributeError):
                category = LogCategory.SYSTEM
            
            # Create and store log message
            message = LogMessage(text=event.message, category=category)
            self.messages.append(message)
            self._update_game_state_log_data()
    
    def _handle_debug_message_event(self, event) -> None:
        """Handle debug message events from the event system."""
        from ..core.events import DebugMessage
        if isinstance(event, DebugMessage):
            # Store as debug category message
            message = LogMessage(text=f"[{event.source}] {event.message}", category=LogCategory.DEBUG)
            self.messages.append(message)
            self._update_game_state_log_data()
    
    def _handle_log_save_request(self, event) -> None:
        """Handle log save request events from the event system."""
        from ..core.events import LogSaveRequested
        if isinstance(event, LogSaveRequested):
            # Call the save log functionality
            success = self.save_log_to_file()
            if success:
                self.system("Log file saved successfully")
            else:
                self.error("Failed to save log file")
    
    def log(self, text: str, category: LogCategory = LogCategory.SYSTEM) -> None:
        """Add a message to the log.
        
        Args:
            text: The message text
            category: The category of the message
        """
        # Always store messages in the buffer for potential display/save later
        message = LogMessage(text=text, category=category)
        self.messages.append(message)
        self._update_game_state_log_data()
    
    # Convenience methods for common categories
    def system(self, text: str) -> None:
        """Log a system message."""
        self.log(text, LogCategory.SYSTEM)
    
    def battle(self, text: str) -> None:
        """Log a battle message."""
        self.log(text, LogCategory.BATTLE)
    
    def movement(self, text: str) -> None:
        """Log a movement message."""
        self.log(text, LogCategory.MOVEMENT)
    
    def ai(self, text: str) -> None:
        """Log an AI message."""
        self.log(text, LogCategory.AI)
    
    def timeline(self, text: str) -> None:
        """Log a timeline message."""
        self.log(text, LogCategory.TIMELINE)
    
    def input(self, text: str) -> None:
        """Log an input message."""
        self.log(text, LogCategory.INPUT)
    
    def debug(self, text: str) -> None:
        """Log a debug message."""
        self.log(text, LogCategory.DEBUG)
    
    def warning(self, text: str) -> None:
        """Log a warning message."""
        self.log(text, LogCategory.WARNING)
    
    def error(self, text: str) -> None:
        """Log an error message."""
        self.log(text, LogCategory.ERROR)
    
    def objective(self, text: str) -> None:
        """Log an objective message."""
        self.log(text, LogCategory.OBJECTIVE)
    
    def interrupt(self, text: str) -> None:
        """Log an interrupt message."""
        self.log(text, LogCategory.INTERRUPT)
    
    def scenario(self, text: str) -> None:
        """Log a scenario message."""
        self.log(text, LogCategory.SCENARIO)
    
    def ui(self, text: str) -> None:
        """Log a UI message."""
        self.log(text, LogCategory.UI)
    
    def get_messages(self, count: Optional[int] = None, 
                     categories: Optional[set[LogCategory]] = None) -> list[LogMessage]:
        """Get recent messages, optionally filtered by category.
        
        Args:
            count: Maximum number of messages to return (None for all)
            categories: Set of categories to include (None for all enabled)
        
        Returns:
            List of recent messages
        """
        # Filter by categories and enabled status
        if categories:
            # Use specific categories requested
            filtered = [msg for msg in self.messages 
                       if msg.category in categories and msg.category in self.enabled_categories]
        else:
            # Use current enabled categories and log level
            filtered = []
            for msg in self.messages:
                # Check if category is enabled
                if msg.category not in self.enabled_categories:
                    continue
                
                # Check log level
                message_level = self.category_levels.get(msg.category, LogLevel.INFO)
                if message_level.value < self.log_level.value:
                    continue
                
                filtered.append(msg)
        
        # Return the most recent messages
        if count is not None and count < len(filtered):
            return list(filtered)[-count:]
        return list(filtered)
    
    def clear(self) -> None:
        """Clear all messages from the log."""
        self.messages.clear()
    
    def enable_category(self, category: LogCategory) -> None:
        """Enable a log category."""
        self.enabled_categories.add(category)
    
    def disable_category(self, category: LogCategory) -> None:
        """Disable a log category."""
        self.enabled_categories.discard(category)
    
    def set_log_level(self, level: LogLevel) -> None:
        """Set the minimum log level."""
        self.log_level = level
    
    def is_debug_enabled(self) -> bool:
        """Check if debug messages are currently enabled."""
        return (LogCategory.DEBUG in self.enabled_categories and 
                self.log_level == LogLevel.DEBUG)
    
    def toggle_debug(self) -> None:
        """Toggle debug message visibility."""
        if self.is_debug_enabled():
            self.disable_category(LogCategory.DEBUG)
            # Set log level back to INFO when disabling debug
            self.set_log_level(LogLevel.INFO)
        else:
            self.enable_category(LogCategory.DEBUG)
            # Set log level to DEBUG to allow debug messages through
            self.set_log_level(LogLevel.DEBUG)
        
        # Update game state with new debug status
        self._update_game_state_log_data()
    
    def save_log_to_file(self) -> bool:
        """Save all messages to a timestamped log file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            from datetime import datetime
            import os
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"log_{timestamp}.log"
            
            # Ensure logs directory exists
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            filepath = os.path.join(log_dir, filename)
            
            # Save all messages with full timestamps and category info
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Grimdark SRPG - Game Log\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                if not self.messages:
                    f.write("No messages to save.\n")
                else:
                    # Save ALL messages from buffer, including debug level (ignore current filters)
                    for msg in self.messages:
                        # Full timestamp format for file
                        timestamp_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # milliseconds
                        category_name = msg.category.name
                        
                        # Write in structured format
                        f.write(f"[{timestamp_str}] [{category_name}] {msg.text}\n")
            
            # Log the save action itself
            self.system(f"Game log saved to {filepath}")
            
            return True
            
        except Exception as e:
            # Log the error but don't crash
            self.error(f"Failed to save log file: {str(e)}")
            return False