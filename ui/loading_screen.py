# =============================================================
# ui/loading_screen.py —— 加载界面
#
# 区域切换时显示过渡加载界面。
#
# 功能：
#   - 暗色背景 + 区域名称
#   - 模拟进度条（0→100%）
#   - 随机世界观提示文字
#   - 绘制完成后自动关闭或等待回调
# =============================================================
from __future__ import annotations
from typing import Optional, List

import pygame
import random

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from config import SCREEN_WIDTH, SCREEN_HEIGHT


# 世界观提示文字（叙事留白）
_LORE_HINTS = [
    "这片烬土曾有一个名字……",
    "火焰熄灭了，但余烬仍在",
    "领主们曾发誓守护这片土地",
    "诅咒降临的那一天，天空裂开了",
    "勇气比剑更锋利",
    "死亡不是终点，遗忘才是",
    "每一块灵魂碎片都是一段记忆",
    "营地之火永不熄灭",
    "古老的力量沉睡在王城深处",
    "英雄终将归来",
]


class LoadingScreen(BaseWidget):
    """
    加载界面。

    用法：
        screen = LoadingScreen()
        screen.start("毒沼泽地")
        while not screen.is_done:
            dt = clock.tick(60) / 1000.0
            screen.update(dt)
            screen.render(display_surface)
    """

    def __init__(self):
        super().__init__(visible=False, z_index=70)
        self._area_name: str = ""
        self._progress: float = 0.0
        self._target_progress: float = 0.0
        self._is_done: bool = False
        self._lore_hint: str = ""
        self._elapsed: float = 0.0

        # 进度条外观
        self._bar_w = 500
        self._bar_h = 12
        self._bar_x = (SCREEN_WIDTH - self._bar_w) // 2
        self._bar_y = SCREEN_HEIGHT // 2 + 80

    @property
    def is_done(self) -> bool:
        return self._is_done and self._progress >= 1.0

    def start(self, area_name: str = "", hint: str = ""):
        """开始加载动画"""
        self.visible = True
        self._area_name = area_name
        self._progress = 0.0
        self._target_progress = 0.0
        self._is_done = False
        self._elapsed = 0.0
        self._lore_hint = hint or random.choice(_LORE_HINTS)

    def set_progress(self, value: float):
        """设置目标进度 [0, 1]"""
        self._target_progress = max(0.0, min(1.0, value))
        if value >= 1.0:
            self._is_done = True

    def finish(self):
        """标记加载完成（进度条走完）"""
        self._target_progress = 1.0
        self._is_done = True

    # ----------------------------------------------------------------
    # 更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        if not self.visible:
            return

        self._elapsed += dt

        # 进度条追赶目标
        if self._progress < self._target_progress:
            self._progress = min(self._target_progress,
                                self._progress + dt * 0.8)
        elif self._is_done and self._progress < 1.0:
            # 完成后再慢慢走满
            self._progress = min(1.0, self._progress + dt * 0.6)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        # 全黑背景
        surface.fill((8, 6, 16))

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        # 标题
        title_font = get_font(22)
        title_surf = title_font.render("烬土传说", True, (180, 170, 140))
        surface.blit(title_surf,
                     title_surf.get_rect(center=(cx, cy - 140)))

        # 区域名称
        if self._area_name:
            area_font = get_font(36, bold=True)
            area_surf = area_font.render(self._area_name, True, (230, 210, 160))
            surface.blit(area_surf,
                         area_surf.get_rect(center=(cx, cy - 70)))

        # 进度条背景
        bar_bg = pygame.Rect(self._bar_x - 2, self._bar_y - 2,
                            self._bar_w + 4, self._bar_h + 4)
        pygame.draw.rect(surface, (40, 38, 55), bar_bg, border_radius=6)

        # 进度条填充
        fill_w = max(0, int(self._bar_w * self._progress))
        if fill_w > 0:
            bar_fill = pygame.Rect(self._bar_x, self._bar_y, fill_w, self._bar_h)
            # 渐变色：暗金 → 亮金
            r = int(100 + 120 * self._progress)
            g = int(80 + 140 * self._progress)
            b = int(40 + 80 * self._progress)
            pygame.draw.rect(surface, (r, g, b), bar_fill, border_radius=6)

        # 进度文字
        pct_font = get_font(16)
        pct_text = f"{int(self._progress * 100)}%"
        pct_surf = pct_font.render(pct_text, True, (200, 200, 215))
        surface.blit(pct_surf, (self._bar_x + self._bar_w + 12,
                               self._bar_y - 2))

        # 世界观提示
        if self._lore_hint:
            hint_font = get_font(18)
            hint_surf = hint_font.render(self._lore_hint, True, (140, 130, 160))
            surface.blit(hint_surf,
                         hint_surf.get_rect(center=(cx, self._bar_y + 60)))
