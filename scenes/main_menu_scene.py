# =============================================================
# scenes/main_menu_scene.py —— 主菜单场景（第一阶段占位版）
# =============================================================

import pygame

from scenes.base_scene import BaseScene
from core.scene_manager import scene_manager
from core.input_handler import input_handler
from utils.color import UI_BG, UI_TEXT, UI_HIGHLIGHT, WHITE
from config import SCREEN_WIDTH, SCREEN_HEIGHT, LAYER_UI
from ui import font_manager


class MainMenuScene(BaseScene):
    """
    第一阶段占位主菜单：
    - 显示游戏标题
    - 显示菜单项（开始游戏 / 退出）
    - 键盘上下选择，Enter 确认
    """

    def __init__(self):
        self._options    = ["开始游戏", "退出"]
        self._selected   = 0
        self._title_font = None
        self._menu_font  = None
        self._tip_font   = None

    def on_enter(self):
        pygame.font.init()
        self._title_font = font_manager.get_font(72, bold=True)
        self._menu_font  = font_manager.get_font(36)
        self._tip_font   = font_manager.get_font(20)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._options)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm()

    def _confirm(self):
        if self._selected == 0:
            from scenes.game_scene import GameScene
            scene_manager.replace(GameScene())
        elif self._selected == 1:
            import sys, pygame
            pygame.quit()
            sys.exit(0)

    def update(self, dt):
        pass

    def render(self, renderer):
        screen = renderer.screen
        screen.fill(UI_BG)

        cx = SCREEN_WIDTH // 2

        # 标题
        title_surf = self._title_font.render("烬土传说", True, UI_HIGHLIGHT)
        screen.blit(title_surf,
                    title_surf.get_rect(center=(cx, SCREEN_HEIGHT // 4)))

        # 副标题
        sub = self._tip_font.render("Ashland Legend  —  v0.1.0  Alpha", True,
                                    (150, 150, 160))
        screen.blit(sub, sub.get_rect(center=(cx, SCREEN_HEIGHT // 4 + 70)))

        # 菜单项
        start_y = SCREEN_HEIGHT // 2
        for i, text in enumerate(self._options):
            color = UI_HIGHLIGHT if i == self._selected else UI_TEXT
            surf  = self._menu_font.render(
                ("▶ " if i == self._selected else "  ") + text,
                True, color
            )
            screen.blit(surf, surf.get_rect(center=(cx, start_y + i * 55)))

        # 底部提示
        tip = self._tip_font.render("↑↓ 移动选项    Enter 确认", True,
                                    (100, 100, 110))
        screen.blit(tip, tip.get_rect(center=(cx, SCREEN_HEIGHT - 40)))

        # 这个场景直接绘制到 screen，不经过 renderer 分层（占位阶段）
        pygame.display.flip()
