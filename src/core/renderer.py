from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

from .renderable import RenderContext
from .input import InputEvent


@dataclass
class RendererConfig:
    width: int = 80
    height: int = 24
    title: str = "SRPG Game"
    target_fps: int = 30


class Renderer(ABC):
    
    def __init__(self, config: Optional[RendererConfig] = None):
        self.config = config or RendererConfig()
        self._running = False
    
    @abstractmethod
    def initialize(self) -> None:
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        pass
    
    @abstractmethod
    def render_frame(self, context: RenderContext) -> None:
        pass
    
    @abstractmethod
    def get_input_events(self) -> list[InputEvent]:
        pass
    
    @abstractmethod
    def clear(self) -> None:
        pass
    
    @abstractmethod
    def present(self) -> None:
        pass
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def start(self) -> None:
        self._running = True
        self.initialize()
    
    def stop(self) -> None:
        self._running = False
        self.cleanup()
    
    def get_screen_size(self) -> tuple[int, int]:
        return (self.config.width, self.config.height)