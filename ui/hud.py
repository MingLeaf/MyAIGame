# =============================================================
# ui/hud.py —— 游戏内 HUD（血条 / 耐力条 / 灵力条）
# =============================================================
from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

from utils.color import COLOR_HP, COLOR_STAMINA, COLOR_MANA, UI_BG, WHITE
from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from config import SCREEN_WIDTH, SCREEN_HEIGHT

if TYPE_CHECKING:
    from entities.player.player import Player


# ---- 布局常量 ----
BAR_X         = 24          # 左边距
BAR_Y_START   = SCREEN_HEIGHT - 90  # 起始 Y
BAR_GAP       = 24          # 条间距
BAR_W         = 220         # 条总宽
BAR_H         = 14          # 条高
BAR_RADIUS    = 4           # 圆角（pygame 2.x）
BG_COLOR      = (30, 25, 35)
BORDER_COLOR  = (60, 55, 70)

# 数字字体
_font = None


def _get_font():
    global _font
    if _font is None:
        _font = get_font(16)
    return _font


class HUD(BaseWidget):
    """
    玩家状态 HUD：
    - HP 条（红）
    - Stamina 条（绿）
    - Mana 条（蓝）
    - 当前状态名（调试）
    """

    def __init__(self):
        super().__init__(visible=True, z_index=40)
        self._hp_anim:       float = 1.0   # 血条动画平滑值（0~1）
        self._stamina_anim:  float = 1.0
        self._mana_anim:     float = 1.0

    def update(self, player: "Player", dt: float):
        """平滑插值血条动画"""
        speed = 6.0  # 插值速度
        self._hp_anim      += (player.stats.hp_ratio - self._hp_anim)      * min(1.0, speed * dt)
        self._stamina_anim += (player.stats.stamina_ratio - self._stamina_anim) * min(1.0, speed * dt)
        self._mana_anim    += (player.stats.mana_ratio - self._mana_anim)   * min(1.0, speed * dt)

    def render(self, surface: pygame.Surface, player: "Player"):
        if not self.visible:
            return
        font = _get_font()
        bars = [
            ("HP",      self._hp_anim,      player.stats.hp_ratio,      COLOR_HP,      player.stats.hp,      player.stats.max_hp),
            ("耐力",    self._stamina_anim,  player.stats.stamina_ratio, COLOR_STAMINA, int(player.stats.stamina), int(player.stats.max_stamina)),
            ("灵力",    self._mana_anim,     player.stats.mana_ratio,    COLOR_MANA,    player.stats.mana,     player.stats.max_mana),
        ]

        for i, (label, anim_ratio, cur_ratio, color, cur_val, max_val) in enumerate(bars):
            bx = BAR_X
            by = BAR_Y_START + i * BAR_GAP

            # ---- 背景 ----
            bg_rect = pygame.Rect(bx, by, BAR_W, BAR_H)
            pygame.draw.rect(surface, BG_COLOR, bg_rect, border_radius=BAR_RADIUS)

            # ---- 延迟条（略微落后于实际值，橙色） ----
            if anim_ratio > cur_ratio:
                delay_w = max(0, int((anim_ratio - cur_ratio) * BAR_W))
                delay_x = bx + int(cur_ratio * BAR_W)
                pygame.draw.rect(surface,
                                 (180, 100, 30),
                                 pygame.Rect(delay_x, by, delay_w, BAR_H),
                                 border_radius=BAR_RADIUS)

            # ---- 实际值 ----
            fill_w = max(0, int(cur_ratio * BAR_W))
            if fill_w > 0:
                pygame.draw.rect(surface, color,
                                 pygame.Rect(bx, by, fill_w, BAR_H),
                                 border_radius=BAR_RADIUS)

            # ---- 边框 ----
            pygame.draw.rect(surface, BORDER_COLOR, bg_rect,
                             width=1, border_radius=BAR_RADIUS)

            # ---- 文字标签 ----
            label_surf = font.render(
                f"{label}  {cur_val}/{max_val}", True, (200, 200, 210))
            surface.blit(label_surf, (bx + BAR_W + 8, by - 1))

        # ---- 调试：当前状态名 ----
        import utils.debug as dbg
        if dbg.enabled:
            state_surf = font.render(
                f"State: {player.current_state}", True, (180, 180, 100))
            surface.blit(state_surf, (BAR_X, BAR_Y_START - 22))

        # ---- 第 8 阶段：灵魂碎片 + 等级显示（右下角）----
        soul_font = get_font(22)
        level = getattr(player.build, "level", 1) if hasattr(player, "build") else 1
        souls = getattr(player, "soul_fragments", 0)
        soul_text = f"◇ {souls}    Lv.{level}"
        soul_surf = soul_font.render(soul_text, True, (200, 220, 255))
        sx = SCREEN_WIDTH - soul_surf.get_width() - 20
        sy = SCREEN_HEIGHT - soul_surf.get_height() - 14
        surface.blit(soul_surf, (sx, sy))
