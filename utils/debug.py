# =============================================================
# utils/debug.py —— 调试工具（碰撞框可视化 / FPS / 日志）
# =============================================================

import logging
from typing import List
import pygame

from config import DEBUG_MODE, DEBUG_SHOW_HITBOX, DEBUG_SHOW_FPS
from utils.color import DEBUG_HITBOX, DEBUG_HURTBOX, WHITE

logger = logging.getLogger("AshlandLegend")

# 全局运行时开关（可在游戏中动态修改）
enabled      = DEBUG_MODE
show_hitbox  = DEBUG_SHOW_HITBOX
show_fps     = DEBUG_SHOW_FPS

# 本帧调试文本行列表（每帧清空）
_debug_lines: List[str] = []


def log(message: str, level: str = "debug"):
    """统一日志输出"""
    getattr(logger, level.lower(), logger.debug)(message)


def add_line(text: str):
    """向本帧调试 HUD 添加一行文字"""
    if enabled:
        _debug_lines.append(text)


def clear_lines():
    """清除本帧调试文字（每帧帧首调用）"""
    _debug_lines.clear()


def draw_rect(surface: pygame.Surface,
              rect: pygame.Rect,
              color=DEBUG_HITBOX,
              width: int = 1):
    """绘制调试矩形（支持半透明 RGBA）"""
    if not (enabled and show_hitbox):
        return
    if len(color) == 4:
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill(color)
        surface.blit(overlay, rect.topleft)
    pygame.draw.rect(surface, color[:3], rect, width)


def draw_circle(surface: pygame.Surface,
                center: tuple,
                radius: float,
                color=(255, 255, 0),
                width: int = 1):
    """绘制调试圆形（例如视野范围）"""
    if not enabled:
        return
    pygame.draw.circle(surface, color, (int(center[0]), int(center[1])),
                       int(radius), width)


def draw_line(surface: pygame.Surface,
              start: tuple,
              end: tuple,
              color=(0, 255, 255),
              width: int = 1):
    """绘制调试线段"""
    if not enabled:
        return
    pygame.draw.line(surface, color,
                     (int(start[0]), int(start[1])),
                     (int(end[0]), int(end[1])),
                     width)


def render(surface: pygame.Surface,
           font: pygame.font.Font,
           fps: float,
           offset_x: int = 8,
           offset_y: int = 8):
    """
    将调试文字渲染到 surface 左上角。
    需要在每帧最后调用。
    """
    if not enabled:
        return

    lines = []
    if show_fps:
        lines.append(f"FPS: {fps:.1f}")
    lines.extend(_debug_lines)

    for i, line in enumerate(lines):
        text_surf = font.render(line, True, WHITE)
        surface.blit(text_surf, (offset_x, offset_y + i * (font.get_height() + 2)))
