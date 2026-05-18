# =============================================================
# ui/main_menu_ui.py —— 主菜单 UI
#
# 覆盖在 MainMenuScene 之上，提供完整的菜单交互。
# 从 scenes/main_menu_scene.py 中抽离 UI 逻辑。
#
# 功能：
#   - 游戏标题动画（渐显 + 浮动）
#   - 菜单按钮（开始游戏 / 继续游戏 / 设置 / 退出）
#   - 粒子背景装饰
#   - 版本号显示
# =============================================================
from __future__ import annotations
from typing import Optional, List, Tuple

import pygame

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from utils.color import UI_BG, UI_TEXT, UI_HIGHLIGHT, WHITE
from config import SCREEN_WIDTH, SCREEN_HEIGHT, GAME_TITLE, GAME_VERSION


class MainMenuUI(BaseWidget):
    """
    主菜单 UI。

    接入方式（MainMenuScene）：
        self._menu_ui = MainMenuUI()
        # handle_events
        action = self._menu_ui.handle_event(event)
        # update
        self._menu_ui.update(dt)
        # render
        self._menu_ui.render(surface)
    """

    def __init__(self):
        super().__init__(visible=True, z_index=50)

        self._options = ["开始游戏", "继续游戏", "设置", "退出"]
        self._selected = 0

        # 动画计时
        self._elapsed: float = 0.0

        # 返回动作队列
        self._pending_action: Optional[str] = None

        # 粒子装饰（简单星点）
        self._particles: List[Tuple[float, float, float]] = []  # (x, y, speed)
        self._init_particles()

    def _init_particles(self):
        """初始化背景装饰粒子"""
        import random
        self._particles = []
        for _ in range(40):
            self._particles.append((
                random.uniform(0, SCREEN_WIDTH),
                random.uniform(0, SCREEN_HEIGHT),
                random.uniform(0.2, 1.0),
            ))

    # ----------------------------------------------------------------
    # 事件处理
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        处理事件。返回 None 表示无操作，
        返回 "start" / "continue" / "settings" / "quit" 表示用户选择。
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

        return None

    def _confirm(self) -> str:
        if self._selected == 0:
            return "start"
        elif self._selected == 1:
            return "continue"
        elif self._selected == 2:
            return "settings"
        elif self._selected == 3:
            return "quit"
        return ""

    # ----------------------------------------------------------------
    # 更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        self._elapsed += dt

        # 更新装饰粒子
        for i, (x, y, speed) in enumerate(self._particles):
            y += speed * 30 * dt
            if y > SCREEN_HEIGHT:
                y = 0
            self._particles[i] = (x, y, speed)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        # 背景
        surface.fill(UI_BG)

        # 装饰粒子
        self._render_particles(surface)

        cx = SCREEN_WIDTH // 2

        # 标题（渐显 + 浮动）
        title_alpha = min(255, int(self._elapsed * 200))
        title_offset_y = int(3 * pygame.math.Vector2(0, 1).rotate(
            self._elapsed * 20).y) if self._elapsed > 1.0 else 0

        title_font = get_font(72, bold=True)
        title_surf = title_font.render(GAME_TITLE, True, UI_HIGHLIGHT)
        if title_alpha < 255:
            title_surf.set_alpha(title_alpha)
        title_rect = title_surf.get_rect(center=(cx, SCREEN_HEIGHT // 4 + title_offset_y))
        surface.blit(title_surf, title_rect)

        # 副标题
        sub_font = get_font(20)
        sub_surf = sub_font.render(
            f"Ashland Legend — v{GAME_VERSION} Alpha",
            True, (150, 150, 160))
        if title_alpha < 255:
            sub_surf.set_alpha(title_alpha)
        surface.blit(sub_surf, sub_surf.get_rect(center=(cx, SCREEN_HEIGHT // 4 + 75)))

        # 菜单项
        menu_font = get_font(36)
        start_y = SCREEN_HEIGHT // 2 - 20
        for i, text in enumerate(self._options):
            is_selected = (i == self._selected)
            prefix = "▶ " if is_selected else "   "
            color = UI_HIGHLIGHT if is_selected else UI_TEXT

            surf = menu_font.render(prefix + text, True, color)
            rect = surf.get_rect(center=(cx, start_y + i * 58))

            # 选中高亮背景
            if is_selected:
                bg_rect = pygame.Rect(rect.x - 16, rect.y - 4,
                                     rect.width + 32, rect.height + 8)
                pygame.draw.rect(surface, (50, 45, 70), bg_rect, border_radius=6)

            surface.blit(surf, rect)

        # 底部提示
        tip_font = get_font(18)
        tip_surf = tip_font.render("↑↓ 移动选项    Enter 确认", True, (100, 100, 110))
        surface.blit(tip_surf, tip_surf.get_rect(center=(cx, SCREEN_HEIGHT - 40)))

    def _render_particles(self, surface: pygame.Surface):
        """绘制背景装饰粒子"""
        for x, y, speed in self._particles:
            # 简单小光点
            alpha = int(60 + 40 * speed)
            color = (80, 70, 110, alpha)
            size = max(1, int(2 * speed))
            pygame.draw.circle(surface, (80, 70, 110),
                             (int(x), int(y)), size)
