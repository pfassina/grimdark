#!/usr/bin/env python3

from src.core.renderer import RendererConfig
from src.renderers.terminal_renderer import TerminalRenderer
from src.game.game import Game


def main():
    config = RendererConfig(
        width=80,
        height=24,
        title="Grimdark SRPG",
        target_fps=30
    )
    
    renderer = TerminalRenderer(config)
    
    game = Game(None, renderer)
    
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise
    finally:
        print("\n\nThanks for playing!")


if __name__ == "__main__":
    main()
