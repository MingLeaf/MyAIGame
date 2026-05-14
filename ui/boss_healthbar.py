# =============================================================
# ui/boss_healthbar.py —— Boss 底部双阶段血条
#
# 第 9 阶段：屏幕底部居中的 Boss 专属血条。
# - 一阶段红色，50% 以下变橙色（二阶段提示）
# - 显示 Boss 名称 + 称号
# - 平滑血量动画
# =============================================================
from __future__ import annotations
import pygame
from typing import Optional

from utils.color import COLOR_HP, UI_HIGHLIGHT, WHITE
from ui.font_manager import get_font


class BossHealthBar:
    """
    Boss 底部血条。

    用法：
        bar.attach(boss)       → 绑定 Boss 实例
        bar.detach()           → 解绑
        bar.update(dt)         → 平滑动画
        bar.render(surface)    → 渲染到屏幕底部
    """

    BAR_W = 600
    BAR_H = 22
    BAR_Y_OFFSET = 50          # 距底部偏移
    BAR_RADIUS = 4

    def __init__(self):
        self._boss: Optional[object] = None
        self._visible: bool = False
        self._hp_anim: float = 1.0   # 平滑血量动画 (0~1)

    def attach(self, boss) -> None:
        self._boss = boss
        self._visible = True
        self._hp_anim = boss.stats.hp_ratio

    def detach(self) -> None:
        self._boss = None
        self._visible = False

    def update(self, dt: float) -> None:
        if self._boss is None:
            return
        target = self._boss.stats.hp_ratio
        self._hp_anim += (target - self._hp_anim) * min(1.0, 8.0 * dt)

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible or self._boss is None:
            return

        sw = surface.get_width()
        sh = surface.get_height()

        bx = (sw - self.BAR_W) // 2
        by = sh - self.BAR_Y_OFFSET - self.BAR_H

        # 背景
        bg_rect = pygame.Rect(bx, by, self.BAR_W, self.BAR_H)
        pygame.draw.rect(surface, (20, 18, 28), bg_rect, border_radius=self.BAR_RADIUS)

        # 血条填充（一阶段红色，二阶段橙色）
        fill_w = max(0, int(self._hp_anim * self.BAR_W))
        phase = getattr(self._boss, "phase", 1)
        color = (180, 40, 30) if phase == 1 else (220, 140, 30)  # 二阶段橙色
        if fill_w > 0:
            fill_rect = pygame.Rect(bx, by, fill_w, self.BAR_H)
            pygame.draw.rect(surface, color, fill_rect, border_radius=self.BAR_RADIUS)

        # 延迟条（略落后于实际）
        actual = self._boss.stats.hp_ratio
        if self._hp_anim > actual:
            delay_w = int((self._hp_anim - actual) * self.BAR_W)
            delay_x = bx + int(actual * self.BAR_W)
            pygame.draw.rect(surface, (220, 200, 100),
                             pygame.Rect(delay_x, by, delay_w, self.BAR_H),
                             border_radius=self.BAR_RADIUS)

        # 边框
        pygame.draw.rect(surface, (80, 75, 100), bg_rect, width=2, border_radius=self.BAR_RADIUS)

        # Boss 名称
        name_font = get_font(18)
        name = getattr(self._boss, "boss_display_name", "Boss")
        title = getattr(self._boss, "boss_title", "")
        if title:
            name = f"{title}·{name}"
        name_surf = name_font.render(name, True, (220, 210, 200))
        surface.blit(name_surf, (bx, by - 22))

        # 血量数字
        hp_font = get_font(14)
        hp_text = f"{self._boss.stats.hp} / {self._boss.stats.max_hp}"
        hp_surf = hp_font.render(hp_text, True, (200, 200, 210))
        surface.blit(hp_surf, (bx + self.BAR_W - hp_surf.get_width() - 4, by - 20))

        # 二阶段标记
        if phase == 2:
            phase_surf = get_font(14).render("◆ 狂化", True, (255, 140, 40))
            surface.blit(phase_surf, (bx + self.BAR_W + 10, by))

        # ---- 韧性/架势条（在 HP 条下方）----
        poise_max = getattr(self._boss.stats, "max_poise", 0)
        if poise_max > 0:
            poise_current = getattr(self._boss.stats, "poise", 0)
            poise_ratio = poise_current / max(1, poise_max)
            POISE_H = 6
            poise_y = by + self.BAR_H + 4
            poise_w = max(0, int(poise_ratio * self.BAR_W))

            # 背景
            pygame.draw.rect(surface, (20, 18, 28),
                             (bx, poise_y, self.BAR_W, POISE_H), border_radius=2)
            # 填充（灰白色）
            if poise_w > 0:
                poise_color = (180, 170, 160) if poise_ratio > 0.3 else (120, 80, 80)
                pygame.draw.rect(surface, poise_color,
                                 (bx, poise_y, poise_w, POISE_H), border_radius=2)
            # 边框
            pygame.draw.rect(surface, (60, 55, 50),
                             (bx, poise_y, self.BAR_W, POISE_H), width=1, border_radius=2)
            # 标签
            poise_label = get_font(11).render("架势", True, (140, 135, 130))
            surface.blit(poise_label, (bx - 28, poise_y - 1))


__all__ = ["BossHealthBar"]
