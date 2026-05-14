# =============================================================
# combat/floating_text.py —— 伤害飘字
#
# FloatingText：单条飘字，从命中点世界坐标向上漂浮 40px，
#               持续 1s，线性 fade-out。
# FloatingTextManager：管理所有活跃飘字，提供 add / update / render。
# =============================================================
from __future__ import annotations

import pygame
from typing import Optional

from ui.font_manager import get_font


# ---- 飘字默认参数 ----
_DEFAULT_LIFETIME  = 1.0    # 飘字生存时间（秒）
_DEFAULT_RISE_PX   = 40     # 向上飘移总像素
_DEFAULT_FONT_SIZE = 18     # 默认字体大小
_DEFAULT_COLOR     = (255, 230, 60)   # 默认亮黄色（普通伤害）
_CRIT_COLOR        = (255, 80,  30)   # 暴击/高伤色
_HEAL_COLOR        = (80,  220, 80)   # 回复色

# 伤害数值大小分级（数值越高字体越大）
_SIZE_THRESHOLDS = [
    (50, 24),   # ≥50 → 字号24
    (20, 20),   # ≥20 → 字号20
    (0,  16),   # 其他 → 字号16
]


def _pick_font_size(value: int) -> int:
    for threshold, size in _SIZE_THRESHOLDS:
        if abs(value) >= threshold:
            return size
    return _DEFAULT_FONT_SIZE


class FloatingText:
    """
    单条飘字实例。

    参数：
        text    : 显示文字（数字字符串或状态名）
        world_x : 命中点世界坐标 X
        world_y : 命中点世界坐标 Y
        color   : RGB 颜色
        size    : 字体大小（0 = 自动按数值分级）
        lifetime: 存活时间（秒）
    """

    def __init__(self,
                 text: str,
                 world_x: int,
                 world_y: int,
                 color: tuple = _DEFAULT_COLOR,
                 size: int = 0,
                 lifetime: float = _DEFAULT_LIFETIME):
        self.text     = text
        self.world_x  = float(world_x)
        self.world_y  = float(world_y)
        self.color    = color
        self.lifetime = lifetime
        self.elapsed  = 0.0
        self.active   = True

        # 自动选字号
        if size <= 0:
            try:
                size = _pick_font_size(int(text))
            except ValueError:
                size = _DEFAULT_FONT_SIZE
        self._font = get_font(size)

        # 预渲染（白边描边，先渲染深色再渲染亮色）
        self._surf: Optional[pygame.Surface] = None

    # ----------------------------------------------------------------

    @property
    def progress(self) -> float:
        """[0, 1]，0=刚出现，1=即将消失"""
        return min(1.0, self.elapsed / self.lifetime)

    def update(self, dt: float) -> bool:
        """更新，返回 True 表示仍存活。"""
        self.elapsed += dt
        if self.elapsed >= self.lifetime:
            self.active = False
        return self.active

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        if not self.active:
            return

        ox, oy = cam_offset
        p      = self.progress

        # 世界坐标 → 屏幕坐标，加上向上漂移
        sx = int(self.world_x - ox)
        sy = int(self.world_y - oy) - int(_DEFAULT_RISE_PX * p)

        # alpha 线性淡出（后 40% 时间开始淡）
        if p < 0.6:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (p - 0.6) / 0.4))
        alpha = max(0, min(255, alpha))

        # 主文字 surface
        text_surf = self._font.render(self.text, True, self.color)
        tw = text_surf.get_width()
        th = text_surf.get_height()

        # 以命中点为中心计算左上角坐标
        draw_x = sx - tw // 2
        draw_y = sy - th // 2

        # 描边：黑色偏移 1px（与主文字对齐，仅向右下偏移）
        shadow_surf = self._font.render(self.text, True, (20, 20, 20))
        shadow_surf.set_alpha(alpha)
        surface.blit(shadow_surf, (draw_x + 1, draw_y + 1))

        # 主文字
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, (draw_x, draw_y))


# ============================================================
# FloatingTextManager
# ============================================================

class FloatingTextManager:
    """
    管理所有活跃飘字。

    用法：
        ftm = FloatingTextManager()

        # 每帧更新
        ftm.update(dt)

        # 每帧渲染（在 HUD 之前、前景层之后）
        ftm.render(surface, cam_offset)

        # 添加伤害数字
        ftm.add_damage(amount, world_x, world_y, is_crit=False)

        # 添加回复数字
        ftm.add_heal(amount, world_x, world_y)

        # 添加任意文字
        ftm.add(text, world_x, world_y, color=..., size=14)
    """

    def __init__(self):
        self._texts: list[FloatingText] = []

    # ----------------------------------------------------------------
    # 工厂方法
    # ----------------------------------------------------------------

    def add_damage(self, amount: int, world_x: int, world_y: int,
                   is_crit: bool = False) -> None:
        color = _CRIT_COLOR if is_crit else _DEFAULT_COLOR
        text  = f"-{amount}" if amount > 0 else "0"
        self._texts.append(FloatingText(text, world_x, world_y, color=color))

    def add_heal(self, amount: int, world_x: int, world_y: int) -> None:
        text = f"+{amount}"
        self._texts.append(FloatingText(text, world_x, world_y, color=_HEAL_COLOR))

    def add(self, text: str, world_x: int, world_y: int,
            color: tuple = _DEFAULT_COLOR,
            size: int = 0,
            lifetime: float = _DEFAULT_LIFETIME) -> None:
        """通用添加接口（用于状态异常文字等）。"""
        self._texts.append(
            FloatingText(text, world_x, world_y, color=color,
                         size=size, lifetime=lifetime)
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

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        for ft in self._texts:
            ft.render(surface, cam_offset)

    def clear(self) -> None:
        self._texts.clear()

    def __len__(self) -> int:
        return len(self._texts)
