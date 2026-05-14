# =============================================================
# scenes/pause_scene.py —— 暂停菜单场景（叠加在游戏场景上层）
# =============================================================

import pygame
from scenes.base_scene  import BaseScene
from core.scene_manager import scene_manager
from utils.color import UI_BG, UI_TEXT, UI_HIGHLIGHT
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from ui.font_manager import get_font


class PauseScene(BaseScene):

    def __init__(self):
        self._font      = None
        self._options   = ["继续游戏", "重新开始", "返回主菜单"]
        self._selected  = 0
        self._overlay   = None

    def on_enter(self):
        pygame.font.init()
        self._font       = get_font(36)
        self._title_font = get_font(52, bold=True)
        # 半透明遮罩
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                       pygame.SRCALPHA)
        self._overlay.fill((10, 8, 20, 180))

    def handle_events(self, events: list):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._options)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm()
                elif event.key == pygame.K_ESCAPE:
                    scene_manager.pop()

    def _confirm(self):
        if self._selected == 0:
            # 继续游戏
            scene_manager.pop()
        elif self._selected == 1:
            # 重新开始：强制重载敌人+篝火，玩家重建
            from scenes.game_scene import GameScene
            scene_manager.clear_and_push(GameScene(restart=True))
        elif self._selected == 2:
            # 返回主菜单
            from scenes.main_menu_scene import MainMenuScene
            scene_manager.clear_and_push(MainMenuScene())

    def update(self, dt: float):
        pass

    def render(self, renderer):
        surface = renderer.screen
        # 遮罩
        surface.blit(self._overlay, (0, 0))
        cx = SCREEN_WIDTH // 2

        # 标题
        title = self._title_font.render("— 暂停 —", True, UI_HIGHLIGHT)
        surface.blit(title, title.get_rect(center=(cx, SCREEN_HEIGHT // 3)))

        # 菜单项
        for i, text in enumerate(self._options):
            color = UI_HIGHLIGHT if i == self._selected else UI_TEXT
            surf  = self._font.render(
                ("▶ " if i == self._selected else "  ") + text,
                True, color
            )
            surface.blit(surf,
                         surf.get_rect(center=(cx, SCREEN_HEIGHT // 2 + i * 55)))

        pygame.display.flip()
