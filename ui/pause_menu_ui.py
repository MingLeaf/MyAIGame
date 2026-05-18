# =============================================================
# ui/pause_menu_ui.py —— 暂停菜单 UI
#
# 覆盖在游戏场景之上，ESC 键触发。
# 从 scenes/pause_scene.py 中抽离 UI 逻辑。
#
# 功能：
#   - 半透明遮罩
#   - 菜单项（继续游戏 / 重新开始 / 设置 / 返回主菜单）
#   - 键盘 W/S/↑↓ 选择，Enter 确认
# =============================================================
from __future__ import annotations
from typing import Optional

import pygame

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from utils.color import UI_BG, UI_TEXT, UI_HIGHLIGHT
from config import SCREEN_WIDTH, SCREEN_HEIGHT


class PauseMenuUI(BaseWidget):
    """
    暂停菜单 UI。
    """

    def __init__(self):
        super().__init__(visible=False, z_index=55)
        self._options = ["继续游戏", "重新开始", "设置", "返回主菜单"]
        self._selected = 0
        self._overlay: Optional[pygame.Surface] = None

    def open(self) -> None:
        self.visible = True
        self._selected = 0
        # 半透明遮罩（懒加载）
        if self._overlay is None:
            self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                          pygame.SRCALPHA)
            self._overlay.fill((10, 8, 20, 180))

    def close(self) -> None:
        self.visible = False

    # ----------------------------------------------------------------
    # 事件
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        处理事件。
        返回 "resume" / "restart" / "settings" / "quit" / None
        """
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(self._options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(self._options)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._confirm()
            elif event.key == pygame.K_ESCAPE:
                return "resume"

        return None

    def _confirm(self) -> str:
        if self._selected == 0:
            return "resume"
        elif self._selected == 1:
            return "restart"
        elif self._selected == 2:
            return "settings"
        elif self._selected == 3:
            return "quit"
        return ""

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        # 遮罩
        if self._overlay:
            surface.blit(self._overlay, (0, 0))
        else:
            # 兜底
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            surface.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        # 标题
        title_font = get_font(52, bold=True)
        title_surf = title_font.render("— 暂停 —", True, UI_HIGHLIGHT)
        surface.blit(title_surf,
                     title_surf.get_rect(center=(cx, cy - 140)))

        # 菜单项
        menu_font = get_font(32)
        for i, text in enumerate(self._options):
            is_sel = (i == self._selected)
            prefix = "▶ " if is_sel else "   "
            color = UI_HIGHLIGHT if is_sel else UI_TEXT

            surf = menu_font.render(prefix + text, True, color)
            rect = surf.get_rect(center=(cx, cy - 40 + i * 55))

            # 高亮背景
            if is_sel:
                bg_rect = pygame.Rect(rect.x - 14, rect.y - 3,
                                     rect.width + 28, rect.height + 6)
                pygame.draw.rect(surface, (50, 45, 70), bg_rect, border_radius=6)

            surface.blit(surf, rect)

        # 底部提示
        tip_font = get_font(16)
        tip_surf = tip_font.render("↑↓ 选择    Enter 确认    ESC 继续", True,
                                   (120, 120, 140))
        surface.blit(tip_surf,
                     tip_surf.get_rect(center=(cx, SCREEN_HEIGHT - 30)))
