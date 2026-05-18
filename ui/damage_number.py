# =============================================================
# ui/damage_number.py —— 伤害飘字系统
#
# 从 combat/floating_text.py 迁移至此，作为 UI 系统的正式模块。
# 扩充功能：按伤害类型着色（火/冰/毒/流血/神圣/灵魂/暴击）。
#
# 核心类：
#   FloatingText          — 单条飘字，从世界坐标向上漂浮 + 淡出
#   FloatingTextManager   — 管理所有活跃飘字，提供工厂方法
#
# 兼容性：
#   combat/floating_text.py 保留为 thin wrapper，from combat.floating_text
#   导入仍可用，实际符号均来自本模块。
# =============================================================
from __future__ import annotations

import pygame
from typing import Optional, Tuple

from ui.font_manager import get_font
from utils.color import (
    DMG_NORMAL, DMG_CRIT, DMG_HEAL,
    DMG_POISON, DMG_FIRE, DMG_ICE, DMG_HOLY,
    WHITE,
)

# ---- 飘字默认参数 ----
_DEFAULT_LIFETIME  = 1.0
_DEFAULT_RISE_PX   = 40
_DEFAULT_FONT_SIZE = 18

# 伤害类型 → 颜色映射（扩充版）
DAMAGE_TYPE_COLORS = {
    "physical": DMG_NORMAL,
    "crit":     DMG_CRIT,
    "heal":     DMG_HEAL,
    "poison":   DMG_POISON,
    "fire":     DMG_FIRE,
    "ice":      DMG_ICE,
    "holy":     DMG_HOLY,
    "bleed":    (200, 30, 60),
    "lightning": (180, 180, 40),
    "soul":     (180, 255, 140),
    "default":  (255, 230, 60),
}

# 伤害数值大小分级
_SIZE_THRESHOLDS = [
    (50, 24),
    (20, 20),
    (0,  16),
]


def _pick_font_size(value: int) -> int:
    for threshold, size in _SIZE_THRESHOLDS:
        if abs(value) >= threshold:
            return size
    return _DEFAULT_FONT_SIZE


# ============================================================
# FloatingText — 单条飘字
# ============================================================

class FloatingText:
    """
    单条飘字实例。

    参数：
        text     : 显示文字（"-25" / "+40" / "暴击!" / "中毒" 等）
        world_x  : 命中点世界坐标 X
        world_y  : 命中点世界坐标 Y
        color    : RGB 颜色元组
        size     : 字体大小（0=自动按数值分级）
        lifetime : 存活时间（秒）
        rise_px  : 向上漂浮像素总量
    """

    __slots__ = (
        "text", "world_x", "world_y", "color", "lifetime",
        "elapsed", "active", "_font", "_surf", "_rise_px",
    )

    def __init__(self,
                 text: str,
                 world_x: int,
                 world_y: int,
                 color: Tuple[int, int, int] = None,
                 size: int = 0,
                 lifetime: float = _DEFAULT_LIFETIME,
                 rise_px: int = _DEFAULT_RISE_PX):
        self.text     = text
        self.world_x  = float(world_x)
        self.world_y  = float(world_y)
        self.color    = color or DAMAGE_TYPE_COLORS["default"]
        self.lifetime = lifetime
        self.elapsed  = 0.0
        self.active   = True
        self._rise_px = rise_px

        if size <= 0:
            try:
                size = _pick_font_size(int(text))
            except ValueError:
                size = _DEFAULT_FONT_SIZE
        self._font = get_font(size)
        self._surf: Optional[pygame.Surface] = None

    @property
    def progress(self) -> float:
        """[0, 1]，0=刚出现，1=即将消失"""
        return min(1.0, self.elapsed / max(self.lifetime, 0.001))

    def update(self, dt: float) -> bool:
        """更新，返回 True 表示仍存活"""
        self.elapsed += dt
        if self.elapsed >= self.lifetime:
            self.active = False
        return self.active

    def render(self, surface: pygame.Surface, cam_offset: Tuple[float, float]) -> None:
        """渲染到屏幕"""
        if not self.active:
            return

        ox, oy = cam_offset
        p = self.progress

        # 世界坐标 → 屏幕坐标 + 向上漂移
        sx = int(self.world_x - ox)
        sy = int(self.world_y - oy) - int(self._rise_px * p)

        # alpha 淡出
        if p < 0.6:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (p - 0.6) / 0.4))
        alpha = max(0, min(255, alpha))

        text_surf = self._font.render(self.text, True, self.color)
        tw, th = text_surf.get_width(), text_surf.get_height()

        draw_x = sx - tw // 2
        draw_y = sy - th // 2

        # 黑色描边
        shadow = self._font.render(self.text, True, (20, 20, 20))
        shadow.set_alpha(alpha)
        surface.blit(shadow, (draw_x + 1, draw_y + 1))

        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (draw_x, draw_y))


# ============================================================
# FloatingTextManager — 飘字管理器
# ============================================================

class FloatingTextManager:
    """
    管理所有活跃飘字。

    用法：
        ftm = FloatingTextManager()
        ftm.update(dt)
        ftm.render(surface, cam_offset)

        # 伤害数字
        ftm.add_damage(amount, wx, wy, dmg_type="physical")
        ftm.add_heal(amount, wx, wy)
        ftm.add_crit(amount, wx, wy)
        ftm.add_status(text, wx, wy, status_type="poison")
        ftm.add(text, wx, wy, color=..., size=...)
    """

    def __init__(self):
        self._texts: list[FloatingText] = []

    # ----------------------------------------------------------------
    # 工厂方法
    # ----------------------------------------------------------------

    def add_damage(self, amount: int, world_x: int, world_y: int,
                   dmg_type: str = "physical",
                   is_crit: bool = False) -> None:
        """添加伤害飘字"""
        color = DAMAGE_TYPE_COLORS.get(dmg_type, DAMAGE_TYPE_COLORS["default"])
        if is_crit:
            color = DAMAGE_TYPE_COLORS["crit"]
            text = f"-{amount}!"
        else:
            text = f"-{amount}" if amount > 0 else "0"
        self._texts.append(FloatingText(text, world_x, world_y, color=color))

    def add_heal(self, amount: int, world_x: int, world_y: int) -> None:
        """添加回复飘字"""
        text = f"+{amount}"
        self._texts.append(
            FloatingText(text, world_x, world_y, color=DAMAGE_TYPE_COLORS["heal"])
        )

    def add_crit(self, amount: int, world_x: int, world_y: int) -> None:
        """添加暴击飘字"""
        text = f"-{amount}!"
        self._texts.append(
            FloatingText(text, world_x, world_y,
                         color=DAMAGE_TYPE_COLORS["crit"],
                         size=24)
        )

    def add_status(self, text: str, world_x: int, world_y: int,
                   status_type: str = "default",
                   lifetime: float = 1.2) -> None:
        """添加状态异常飘字（"中毒"/"燃烧"/"冰冻"/"流血"等）"""
        color = DAMAGE_TYPE_COLORS.get(status_type, DAMAGE_TYPE_COLORS["default"])
        self._texts.append(
            FloatingText(text, world_x, world_y, color=color,
                         size=15, lifetime=lifetime)
        )

    def add(self, text: str, world_x: int, world_y: int,
            color: Tuple[int, int, int] = None,
            size: int = 0,
            lifetime: float = _DEFAULT_LIFETIME,
            rise_px: int = _DEFAULT_RISE_PX) -> None:
        """通用添加接口"""
        self._texts.append(
            FloatingText(text, world_x, world_y,
                         color=color or DAMAGE_TYPE_COLORS["default"],
                         size=size, lifetime=lifetime, rise_px=rise_px)
        )

    # ----------------------------------------------------------------
    # 每帧更新 / 渲染
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        alive = []
        for ft in self._texts:
            if ft.update(dt):
                alive.append(ft)
        self._texts = alive

    def render(self, surface: pygame.Surface, cam_offset: Tuple[float, float]) -> None:
        for ft in self._texts:
            ft.render(surface, cam_offset)

    def clear(self) -> None:
        self._texts.clear()

    def __len__(self) -> int:
        return len(self._texts)
