# =============================================================
# scenes/main_menu_scene.py —— 主菜单场景
# =============================================================

import pygame, sys

from scenes.base_scene import BaseScene
from core.scene_manager import scene_manager
from utils.color import UI_BG
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from ui.main_menu_ui import MainMenuUI


class MainMenuScene(BaseScene):
    """
    主菜单场景。委托 MainMenuUI 处理渲染和输入。
    """

    def __init__(self):
        self._menu_ui = MainMenuUI()

    def on_enter(self):
        pygame.font.init()
        self._menu_ui.visible = True

    def handle_events(self, events: list):
        for event in events:
            action = self._menu_ui.handle_event(event)
            if action is None:
                continue

            if action == "start":
                from scenes.game_scene import GameScene
                scene_manager.replace(GameScene())
            elif action == "continue":
                # 暂未实现存档，效果同开始游戏
                from scenes.game_scene import GameScene
                scene_manager.replace(GameScene())
            elif action == "settings":
                from scenes.settings_scene import SettingsScene
                scene_manager.push(SettingsScene())
            elif action == "quit":
                pygame.quit()
                sys.exit(0)

    def update(self, dt: float):
        self._menu_ui.update(dt)

    def render(self, renderer):
        surface = renderer.screen
        self._menu_ui.render(surface)
        pygame.display.flip()
