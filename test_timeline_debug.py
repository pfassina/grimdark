#!/usr/bin/env python3
"""Debug script to walk through timeline logic and understand unit scheduling order."""

from src.core.engine.timeline import TimelineEntry

# Simulate the unit data from default_test.yaml scenario
units_data = [
    # Units added in scenario order (PLAYER team first, then ENEMY team)
    {"name": "Knight 1", "team": "PLAYER", "speed": 3, "unit_id": "p1"},
    {"name": "Archer 1", "team": "PLAYER", "speed": 6, "unit_id": "p2"}, 
    {"name": "Mage 1", "team": "PLAYER", "speed": 4, "unit_id": "p3"},
    {"name": "Enemy Knight", "team": "ENEMY", "speed": 3, "unit_id": "e1"},
    {"name": "Enemy Archer", "team": "ENEMY", "speed": 6, "unit_id": "e2"},
    {"name": "Enemy Warrior", "team": "ENEMY", "speed": 5, "unit_id": "e3"},
]

def debug_timeline_scheduling():
    """Walk through the exact timeline scheduling logic."""
    print("=== TIMELINE SCHEDULING DEBUG ===\n")
    
    print("1. INITIAL SCHEDULING:")
    print("Adding units to timeline with action_weight=0 (like initialize_battle_timeline)")
    
    entries = []
    
    # Simulate the initialization process
    for i, unit in enumerate(units_data):
        # Calculate execution time: current_time + base_speed + action_weight
        # current_time = 0, action_weight = 0 (from initialize_battle_timeline)
        execution_time = 0 + unit["speed"] + 0
        
        # Create entry manually to show sequence_id assignment
        entry = TimelineEntry(
            execution_time=execution_time,
            entity_id=unit["unit_id"], 
            entity_type="unit",
            sequence_id=i + 1,  # sequence IDs start at 1 and increment
            action_description="Ready to Act"
        )
        entries.append(entry)
        
        print(f"  {unit['name']} ({unit['team']}): time={execution_time}, sequence_id={entry.sequence_id}")
    
    print("\n2. TIMELINE QUEUE ORDER:")
    print("Entries sorted by execution_time first, then sequence_id for ties:")
    
    # Sort using the same logic as timeline (execution_time primary, sequence_id secondary)
    sorted_entries = sorted(entries, key=lambda e: (e.execution_time, e.sequence_id))
    
    for i, entry in enumerate(sorted_entries, 1):
        unit = next(u for u in units_data if u["unit_id"] == entry.entity_id)
        print(f"  {i}. {unit['name']} ({unit['team']}) - time={entry.execution_time}, seq={entry.sequence_id}")
    
    print("\n3. TURN EXECUTION ORDER:")
    print("This is the order units will take their turns:")
    
    turn_number = 1
    for entry in sorted_entries:
        unit = next(u for u in units_data if u["unit_id"] == entry.entity_id)
        print(f"  Turn {turn_number}: {unit['name']} ({unit['team']})")
        turn_number += 1
    
    print("\n4. ANALYSIS:")
    print("Notice the pattern:")
    
    # Group by execution time
    by_time = {}
    for entry in sorted_entries:
        time = entry.execution_time
        if time not in by_time:
            by_time[time] = []
        unit = next(u for u in units_data if u["unit_id"] == entry.entity_id)
        by_time[time].append((unit["name"], unit["team"], entry.sequence_id))
    
    for time in sorted(by_time.keys()):
        units_at_time = by_time[time]
        if len(units_at_time) > 1:
            print(f"  Time {time}: {len(units_at_time)} units tied")
            for name, team, seq in units_at_time:
                print(f"    - {name} ({team}) seq={seq}")
            print(f"    → Winner: {units_at_time[0][0]} (lowest sequence_id)")
        else:
            name, team, seq = units_at_time[0]
            print(f"  Time {time}: {name} ({team}) - no tie")
    
    print("\n5. ROOT CAUSE:")
    print("The 'batching' pattern happens because:")
    print("1. All units start with action_weight=0, so execution_time = speed")
    print("2. Units are added to timeline in scenario order (PLAYER team first)")
    print("3. Sequential sequence_ids favor earlier-added units in ties")
    print("4. Result: PLAYER units win ties and cluster together in turn order")


if __name__ == "__main__":
    debug_timeline_scheduling()