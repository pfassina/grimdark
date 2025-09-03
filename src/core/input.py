from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Any


class InputType(Enum):
    KEY_PRESS = auto()
    KEY_RELEASE = auto()
    MOUSE_MOVE = auto()
    MOUSE_CLICK = auto()
    MOUSE_RELEASE = auto()
    QUIT = auto()


class Key(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    ENTER = auto()
    SPACE = auto()
    ESCAPE = auto()
    TAB = auto()
    
    A = auto()
    B = auto()
    C = auto()
    D = auto()
    E = auto()
    F = auto()
    G = auto()
    H = auto()
    I = auto()  # noqa: E741
    J = auto()
    K = auto()
    L = auto()
    M = auto()
    N = auto()
    O = auto()  # noqa: E741
    P = auto()
    Q = auto()
    R = auto()
    S = auto()
    T = auto()
    U = auto()
    V = auto()
    W = auto()
    X = auto()
    Y = auto()
    Z = auto()
    
    NUM_0 = auto()
    NUM_1 = auto()
    NUM_2 = auto()
    NUM_3 = auto()
    NUM_4 = auto()
    NUM_5 = auto()
    NUM_6 = auto()
    NUM_7 = auto()
    NUM_8 = auto()
    NUM_9 = auto()
    
    F1 = auto()
    F2 = auto()
    F3 = auto()
    F4 = auto()
    F5 = auto()
    F6 = auto()
    F7 = auto()
    F8 = auto()
    F9 = auto()
    F10 = auto()
    F11 = auto()
    F12 = auto()
    
    HELP = auto()  # For ? key
    
    SHIFT = auto()
    CTRL = auto()
    ALT = auto()
    
    UNKNOWN = auto()


class MouseButton(Enum):
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


@dataclass
class InputEvent:
    event_type: InputType
    key: Optional[Key] = None
    mouse_button: Optional[MouseButton] = None
    mouse_x: Optional[int] = None
    mouse_y: Optional[int] = None
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    raw_data: Optional[Any] = None
    
    @classmethod
    def quit_event(cls) -> "InputEvent":
        return cls(event_type=InputType.QUIT)
    
    @classmethod
    def key_press(cls, key: Key, shift: bool = False, ctrl: bool = False, alt: bool = False) -> "InputEvent":
        return cls(
            event_type=InputType.KEY_PRESS,
            key=key,
            shift=shift,
            ctrl=ctrl,
            alt=alt
        )
    
    @classmethod
    def mouse_click(cls, x: int, y: int, button: MouseButton = MouseButton.LEFT) -> "InputEvent":
        return cls(
            event_type=InputType.MOUSE_CLICK,
            mouse_x=x,
            mouse_y=y,
            mouse_button=button
        )
    
    def is_movement_key(self) -> bool:
        return self.key in {Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT, Key.S, Key.D}
    
    def is_confirm_key(self) -> bool:
        return self.key in {Key.ENTER, Key.SPACE, Key.Z}
    
    def is_cancel_key(self) -> bool:
        return self.key in {Key.ESCAPE, Key.X}
    
    def is_menu_key(self) -> bool:
        return self.key in {Key.TAB, Key.M}


class InputHandler:
    
    def __init__(self):
        self._callbacks = {}
    
    def register_callback(self, event_type: InputType, callback):
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)
    
    def handle_event(self, event: InputEvent) -> bool:
        if event.event_type in self._callbacks:
            for callback in self._callbacks[event.event_type]:
                if callback(event):
                    return True
        return False
    
    def clear_callbacks(self):
        self._callbacks.clear()