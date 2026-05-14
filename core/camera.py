# =============================================================
# core/camera.py —— 摄像机（跟随 / 视口裁剪 / 震动）
# =============================================================

import math
import random
from typing import Optional, Tuple
import pygame

from config import SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_SMOOTH
from utils.math_utils import lerp, clamp


class Camera:
    """
    2D 摄像机。
    - 平滑跟随目标
    - 世界坐标 ↔ 屏幕坐标转换
    - 屏幕震动效果
    - 可选边界限制（世界地图尺寸）
    """

    def __init__(self,
                 viewport_width: int  = SCREEN_WIDTH,
                 viewport_height: int = SCREEN_HEIGHT):
        self._vp_w   = viewport_width
        self._vp_h   = viewport_height

        # 摄像机左上角在世界中的坐标（浮点精度）
        self._x: float = 0.0
        self._y: float = 0.0

        # 震动参数
        self._shake_duration: float  = 0.0
        self._shake_intensity: float = 0.0
        self._shake_offset: Tuple[float, float] = (0.0, 0.0)

        # 世界边界（None = 无限制）
        self._bounds: Optional[pygame.Rect] = None

        # 平滑系数
        self.smooth = CAMERA_SMOOTH

    # ---- 更新 ----

    def update(self, dt: float, target_rect: Optional[pygame.Rect] = None):
        """
        每帧调用。
        :param target_rect: 跟随目标的世界坐标矩形（通常是玩家 rect）
        """
        if target_rect is not None:
            # 目标位置：让目标居于视口中央
            goal_x = target_rect.centerx - self._vp_w / 2
            goal_y = target_rect.centery - self._vp_h / 2
            # 平滑插值
            t = clamp(self.smooth * dt, 0.0, 1.0)
            self._x = lerp(self._x, goal_x, t)
            self._y = lerp(self._y, goal_y, t)

        # 限制在世界边界内
        if self._bounds:
            self._x = clamp(self._x, self._bounds.left,
                            self._bounds.right  - self._vp_w)
            self._y = clamp(self._y, self._bounds.top,
                            self._bounds.bottom - self._vp_h)

        # 更新震动
        if self._shake_duration > 0:
            self._shake_duration -= dt
            if self._shake_duration <= 0:
                self._shake_duration = 0
                self._shake_offset   = (0, 0)
            else:
                ox = random.uniform(-1, 1) * self._shake_intensity
                oy = random.uniform(-1, 1) * self._shake_intensity
                self._shake_offset = (ox, oy)
        else:
            self._shake_offset = (0, 0)

    # ---- 震动 ----

    def shake(self, duration: float, intensity: float):
        """触发屏幕震动。duration：秒，intensity：像素"""
        self._shake_duration  = duration
        self._shake_intensity = intensity

    # ---- 坐标转换 ----

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        """世界坐标 → 屏幕坐标"""
        sx = wx - self._x + self._shake_offset[0]
        sy = wy - self._y + self._shake_offset[1]
        return (int(sx), int(sy))

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        """屏幕坐标 → 世界坐标"""
        return (sx + self._x - self._shake_offset[0],
                sy + self._y - self._shake_offset[1])

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        """将世界坐标矩形转换为屏幕坐标矩形（不修改原矩形）"""
        return rect.move(
            -int(self._x) + int(self._shake_offset[0]),
            -int(self._y) + int(self._shake_offset[1])
        )

    def apply_offset(self) -> Tuple[int, int]:
        """返回当前偏移量（用于手动偏移）"""
        return (int(self._x - self._shake_offset[0]),
                int(self._y - self._shake_offset[1]))

    # ---- 视口裁剪 ----

    def is_visible(self, rect: pygame.Rect, margin: int = 64) -> bool:
        """判断世界坐标矩形是否在视口内（含 margin 缓冲）"""
        vp = pygame.Rect(self._x - margin, self._y - margin,
                         self._vp_w + margin * 2,
                         self._vp_h + margin * 2)
        return vp.colliderect(rect)

    # ---- 边界设置 ----

    def set_bounds(self, world_rect: pygame.Rect):
        self._bounds = world_rect

    def clear_bounds(self):
        self._bounds = None

    # ---- 直接定位 ----

    def set_position(self, x: float, y: float):
        self._x = x
        self._y = y

    def center_on(self, wx: float, wy: float):
        self._x = wx - self._vp_w / 2
        self._y = wy - self._vp_h / 2

    # ---- 属性 ----

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def viewport_rect(self) -> pygame.Rect:
        """摄像机在世界坐标中的可视区域"""
        return pygame.Rect(int(self._x), int(self._y),
                           self._vp_w, self._vp_h)
