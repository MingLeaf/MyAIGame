# =============================================================
# utils/rect_utils.py —— 矩形辅助工具
# =============================================================

import pygame


def rect_overlap(a: pygame.Rect, b: pygame.Rect) -> bool:
    """AABB 碰撞检测（是否重叠）"""
    return a.colliderect(b)


def overlap_depth(a: pygame.Rect, b: pygame.Rect) -> tuple[float, float]:
    """
    返回两个矩形在 X、Y 轴的重叠深度（带符号）。
    正值表示 a 在 b 右侧/下方需要向右/下推出。
    """
    ax = (a.centerx - b.centerx)
    ay = (a.centery - b.centery)

    half_w = (a.width + b.width) / 2
    half_h = (a.height + b.height) / 2

    depth_x = half_w - abs(ax)
    depth_y = half_h - abs(ay)

    if depth_x <= 0 or depth_y <= 0:
        return (0.0, 0.0)

    sign_x = 1 if ax > 0 else -1
    sign_y = 1 if ay > 0 else -1
    return (depth_x * sign_x, depth_y * sign_y)


def expand_rect(rect: pygame.Rect, amount: int) -> pygame.Rect:
    """将矩形向四周等量扩展"""
    return rect.inflate(amount * 2, amount * 2)


def rect_from_center(cx: float, cy: float,
                     w: int, h: int) -> pygame.Rect:
    """以中心点创建矩形"""
    return pygame.Rect(cx - w // 2, cy - h // 2, w, h)


def clamp_rect_inside(inner: pygame.Rect,
                      outer: pygame.Rect) -> pygame.Rect:
    """将 inner 矩形限制在 outer 矩形内部，返回调整后的新矩形"""
    x = max(outer.left, min(inner.left, outer.right  - inner.width))
    y = max(outer.top,  min(inner.top,  outer.bottom - inner.height))
    return pygame.Rect(x, y, inner.width, inner.height)


def point_in_rect(point: tuple, rect: pygame.Rect) -> bool:
    """判断点是否在矩形内"""
    return rect.collidepoint(point)


def rects_to_surface_coords(rect: pygame.Rect,
                             camera_offset: tuple) -> pygame.Rect:
    """将世界坐标矩形转换为屏幕坐标矩形"""
    return rect.move(-camera_offset[0], -camera_offset[1])
