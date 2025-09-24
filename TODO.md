# List of TODOs


* update unit tests
* we should probably simplify component.status.can_* .. it is just a reference to self.has_*. We should also consider if we need mark_*. We should also look at how this bubbles up to the Unit class.
* When exiting from Inspect mode, the cursor should be positioned in the current unit's position.
* This pattern where we create an action to publish an event seems cumbersome: `wait_action = Wait()`
* Why handle_action_targeting() exists, if all it foes is self.execute_unit_action()?

## Future TODOs
* Create a SDL/OpenGL renderer
* Implement Morale
* Implement Interrupt
* Implement Harzard
* Implement Wounds
