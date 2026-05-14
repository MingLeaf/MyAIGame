# =============================================================
# physics/collision_detector.py —— 碰撞检测（AABB / 圆形）
# =============================================================

from __future__ import annotations
from typing import List, Tuple, Optional
import pygame
import math


class CollisionDetector:
    """
    轻量级碰撞检测工具集（静态方法）。
    """

    # ---- AABB ----

    @staticmethod
    def aabb(a: pygame.Rect, b: pygame.Rect) -> bool:
        """矩形 AABB 碰撞检测"""
        return a.colliderect(b)

    @staticmethod
    def aabb_overlap(a: pygame.Rect, b: pygame.Rect) -> Tuple[float, float]:
        """
        返回两矩形在 X、Y 轴的重叠深度（带符号）。
        正值表示 a 在 b 的右侧/下方（即需要把 a 向右/下推出）。
        若无重叠则返回 (0, 0)。
        """
        if not a.colliderect(b):
            return (0.0, 0.0)

        ax = float(a.centerx - b.centerx)
        ay = float(a.centery - b.centery)
        half_w = (a.width  + b.width)  / 2.0
        half_h = (a.height + b.height) / 2.0

        depth_x = half_w - abs(ax)
        depth_y = half_h - abs(ay)

        sign_x = 1 if ax >= 0 else -1
        sign_y = 1 if ay >= 0 else -1
        return (depth_x * sign_x, depth_y * sign_y)

    @staticmethod
    def point_in_rect(point: Tuple[float, float], rect: pygame.Rect) -> bool:
        return rect.collidepoint(int(point[0]), int(point[1]))

    @staticmethod
    def rect_contains(outer: pygame.Rect, inner: pygame.Rect) -> bool:
        return outer.contains(inner)

    # ---- 圆形 ----

    @staticmethod
    def circle(cx1: float, cy1: float, r1: float,
               cx2: float, cy2: float, r2: float) -> bool:
        dx = cx1 - cx2
        dy = cy1 - cy2
        return (dx * dx + dy * dy) <= (r1 + r2) ** 2

    @staticmethod
    def circle_rect(cx: float, cy: float, radius: float,
                    rect: pygame.Rect) -> bool:
        """圆形与矩形碰撞"""
        closest_x = max(rect.left, min(cx, rect.right))
        closest_y = max(rect.top,  min(cy, rect.bottom))
        dx = cx - closest_x
        dy = cy - closest_y
        return (dx * dx + dy * dy) <= radius * radius

    # ---- 射线 ----

    @staticmethod
    def ray_rect(origin: Tuple[float, float],
                 direction: Tuple[float, float],
                 length: float,
                 rect: pygame.Rect) -> Optional[Tuple[float, float]]:
        """
        射线与矩形相交检测。
        返回第一个交点坐标，无交点返回 None。
        """
        ox, oy = origin
        dx, dy = direction
        # 归一化
        mag = math.sqrt(dx * dx + dy * dy)
        if mag == 0:
            return None
        dx /= mag
        dy /= mag

        # 检测线段上若干采样点（简化实现）
        steps = max(1, int(length / 8))
        step_len = length / steps
        for i in range(steps + 1):
            t  = i * step_len
            px = ox + dx * t
            py = oy + dy * t
            if rect.collidepoint(int(px), int(py)):
                return (px, py)
        return None
