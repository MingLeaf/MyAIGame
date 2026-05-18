# =============================================================
# scenes/pause_scene.py —— 暂停菜单场景（叠加在游戏场景上层）
# =============================================================

import pygame

from scenes.base_scene  import BaseScene
from core.scene_manager import scene_manager
from ui.pause_menu_ui import PauseMenuUI
from config import SCREEN_WIDTH, SCREEN_HEIGHT


class PauseScene(BaseScene):
    """
    暂停菜单场景。委托 PauseMenuUI 处理。
    """

    def __init__(self):
        self._pause_ui = PauseMenuUI()

    def on_enter(self):
        pygame.font.init()
        self._pause_ui.open()

    def on_exit(self):
        self._pause_ui.close()

    def handle_events(self, events: list):
        for event in events:
            action = self._pause_ui.handle_event(event)
            if action is None:
                continue

            if action == "resume":
                scene_manager.pop()
            elif action == "restart":
                from scenes.game_scene import GameScene
                scene_manager.clear_and_push(GameScene(restart=True))
            elif action == "settings":
                from scenes.settings_scene import SettingsScene
                scene_manager.push(SettingsScene())
            elif action == "quit":
                from scenes.main_menu_scene import MainMenuScene
                scene_manager.clear_and_push(MainMenuScene())

    def update(self, dt: float):
        pass

    def render(self, renderer):
        surface = renderer.screen
        self._pause_ui.render(surface)
        pygame.display.flip()
