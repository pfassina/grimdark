import json
import os
from dataclasses import dataclass
from typing import Optional

import yaml

from ..core.input import InputEvent, Key
from .scenario import Scenario
from .scenario_loader import ScenarioLoader


@dataclass
class ScenarioInfo:
    """Metadata about a scenario for menu display."""

    name: str
    description: str
    author: str = ""
    file_path: str = ""


class ScenarioMenu:
    """Handles scenario discovery, display, and selection."""

    def __init__(self, scenarios_dir: str = "assets/scenarios"):
        self.scenarios_dir = scenarios_dir
        self.scenarios: list[ScenarioInfo] = []
        self.selected_index = 0
        self.display_items: list[str] = []
        self.scenario_map: list[int] = []  # Maps display line to scenario index
        self.selected_display_line = 0
        self.discover_scenarios()

    def discover_scenarios(self) -> None:
        """Scan the scenarios directory and load scenario metadata."""
        self.scenarios = []

        if not os.path.exists(self.scenarios_dir):
            # print(f"Warning: scenarios directory '{self.scenarios_dir}' not found")
            return

        for filename in os.listdir(self.scenarios_dir):
            if filename.endswith(".yaml"):
                file_path = os.path.join(self.scenarios_dir, filename)
                try:
                    scenario_info = self._load_scenario_info(file_path)
                    if scenario_info:
                        self.scenarios.append(scenario_info)
                except Exception as e:
                    print(f"Warning: Failed to load scenario {filename}: {e}")

        # Sort by name for consistent ordering
        self.scenarios.sort(key=lambda s: s.name)

    def _load_scenario_info(self, file_path: str) -> Optional[ScenarioInfo]:
        """Load basic scenario metadata without full scenario parsing."""
        try:
            with open(file_path, "r") as f:
                if file_path.endswith(".yaml"):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            return ScenarioInfo(
                name=data.get("name", "Unknown Scenario"),
                description=data.get("description", "No description available"),
                author=data.get("author", "Unknown Author"),
                file_path=file_path,
            )
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            # print(f"Error loading scenario info from {file_path}: {e}")
            return None

    def get_scenario_count(self) -> int:
        """Get the number of available scenarios."""
        return len(self.scenarios)

    def get_selected_scenario_info(self) -> Optional[ScenarioInfo]:
        """Get the currently selected scenario info."""
        if 0 <= self.selected_index < len(self.scenarios):
            return self.scenarios[self.selected_index]
        return None

    def get_menu_items(
        self, max_width: Optional[int] = None
    ) -> tuple[list[str], list[int]]:
        """Get formatted menu items for display.

        Returns:
            tuple of (display_items, scenario_map) where scenario_map maps display line index to scenario index
        """
        items = []
        scenario_map = []  # Maps display line index to scenario index

        # Calculate available width for content (subtract menu borders and prefix)
        content_width = max_width - 4 if max_width else None

        for scenario_idx, scenario in enumerate(self.scenarios):
            # Calculate full single-line length
            full_line_len = len(scenario.name) + (
                len(scenario.description) + 3 if scenario.description else 0
            )

            if content_width and full_line_len > content_width:
                # Multi-line format when combined text is too long
                items.append(scenario.name)
                scenario_map.append(scenario_idx)  # Title line belongs to this scenario

                if scenario.description:
                    # Add description as separate indented line(s)
                    if (
                        len(scenario.description) + 2 <= content_width
                    ):  # Account for indentation
                        items.append(f"  {scenario.description}")
                        scenario_map.append(
                            scenario_idx
                        )  # Description line also belongs to this scenario
                    else:
                        # Break description into multiple lines
                        words = scenario.description.split()
                        current_line = "  "
                        for word in words:
                            # Check if adding this word would exceed width
                            test_line = (
                                current_line
                                + (" " if len(current_line) > 2 else "")
                                + word
                            )
                            if len(test_line) <= content_width:
                                current_line = test_line
                            else:
                                # Current line is full, start new line
                                if (
                                    len(current_line) > 2
                                ):  # Has content beyond indentation
                                    items.append(current_line)
                                    scenario_map.append(scenario_idx)
                                current_line = f"  {word}"

                        # Add final line if it has content
                        if len(current_line) > 2:
                            items.append(current_line)
                            scenario_map.append(scenario_idx)
            else:
                # Single line format when it fits
                item = scenario.name
                if scenario.description:
                    item += f" - {scenario.description}"
                items.append(item)
                scenario_map.append(scenario_idx)

        if not items:
            items = ["No scenarios found"]
            scenario_map = [0]

        return items, scenario_map

    def update_display_items(self, max_width: Optional[int] = None) -> None:
        """Update the display items and mapping based on current width."""
        self.display_items, self.scenario_map = self.get_menu_items(max_width)
        # Update selected display line to match current scenario
        self._update_selected_display_line()

    def _update_selected_display_line(self) -> None:
        """Update selected_display_line to show the scenario title line."""
        # Find the first display line that corresponds to the selected scenario
        for i, scenario_idx in enumerate(self.scenario_map):
            if scenario_idx == self.selected_index:
                self.selected_display_line = i
                break

    def handle_input(self, event: InputEvent) -> Optional[str]:
        """
        Handle menu navigation input.

        Returns:
            'load' if user selected to load scenario
            'quit' if user wants to quit
            None if no action taken
        """
        if event.key == Key.UP or event.key == Key.W:
            if self.scenarios:
                self.selected_index = (self.selected_index - 1) % len(self.scenarios)
                self._update_selected_display_line()

        elif event.key == Key.DOWN or event.key == Key.S:
            if self.scenarios:
                self.selected_index = (self.selected_index + 1) % len(self.scenarios)
                self._update_selected_display_line()

        elif event.is_confirm_key():  # Enter or Z
            if self.scenarios and 0 <= self.selected_index < len(self.scenarios):
                return "load"

        elif event.key == Key.Q:
            return "quit"

        return None

    def load_selected_scenario(self) -> Optional[Scenario]:
        """Load the currently selected scenario."""
        selected_info = self.get_selected_scenario_info()
        if not selected_info:
            return None

        try:
            return ScenarioLoader.load_from_file(selected_info.file_path)
        except Exception:
            # print(f"Error loading scenario {selected_info.name}: {e}")
            return None

