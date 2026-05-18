# =============================================================
# scenes/settings_scene.py —— 设置场景
# =============================================================

import pygame

from scenes.base_scene import BaseScene
from core.scene_manager import scene_manager
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from ui.settings_ui import SettingsUI


class SettingsScene(BaseScene):
    """
    设置场景。作为叠加层 push 到场景栈上。
    ESC 或取消 → pop 回上一个场景。
    """

    def __init__(self):
        self._settings_ui = SettingsUI()

    def on_enter(self):
        pygame.font.init()
        self._settings_ui.open()

    def on_exit(self):
        self._settings_ui.close()

    def handle_events(self, events: list):
        for event in events:
            action = self._settings_ui.handle_event(event)
            if action == "cancel":
                scene_manager.pop()
            # apply 即时生效

    def update(self, dt: float):
        self._settings_ui.update(dt)

    def render(self, renderer):
        surface = renderer.screen
        self._settings_ui.render(surface)
        pygame.display.flip()
