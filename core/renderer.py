# =============================================================
# core/renderer.py —— 渲染器，管理分层绘制
# =============================================================

from __future__ import annotations
import pygame
from typing import Dict, List, Tuple, Optional, Union
from config import (SCREEN_WIDTH, SCREEN_HEIGHT,
                    LAYER_BACKGROUND, LAYER_UI)
from utils.color import BLACK


class RenderLayer:
    """单个渲染层：持有一组绘制调用"""

    def __init__(self, z_order: int):
        self.z_order = z_order
        # 每帧收集到的绘制命令列表：[(surface, dest_rect), ...]
        self._commands: List[Tuple[pygame.Surface, tuple]] = []

    def add(self, surface: pygame.Surface, dest: Union[tuple, pygame.Rect]):
        self._commands.append((surface, dest))

    def clear(self):
        self._commands.clear()

    def flush_to(self, target: pygame.Surface):
        for surf, dest in self._commands:
            target.blit(surf, dest)
        self._commands.clear()


class Renderer:
    """
    分层渲染器。

    用法：
        renderer.begin()                         # 帧首清屏
        renderer.draw(surface, pos, layer=...)   # 收集绘制命令
        renderer.end()                           # 按层顺序 blit 到屏幕
    """

    def __init__(self, screen: pygame.Surface):
        self._screen  = screen
        self._layers: Dict[int, RenderLayer] = {}
        self._bg_color = BLACK

        # 预创建标准层
        for z in (LAYER_BACKGROUND, 10, 20, 25, 30, 35, LAYER_UI):
            self._get_or_create(z)

    # ---- 内部工具 ----

    def _get_or_create(self, z: int) -> RenderLayer:
        if z not in self._layers:
            self._layers[z] = RenderLayer(z)
        return self._layers[z]

    # ---- 公共接口 ----

    def begin(self, bg_color: tuple | None = None):
        """帧首：清屏"""
        self._screen.fill(bg_color or self._bg_color)

    def draw(self, surface: pygame.Surface,
             dest: Union[tuple, pygame.Rect],
             layer: int = 20):
        """向指定层添加绘制命令"""
        self._get_or_create(layer).add(surface, dest)

    def draw_rect(self, color: tuple,
                  rect: pygame.Rect,
                  width: int = 0,
                  layer: int = LAYER_UI):
        """绘制矩形（创建临时 surface 放入对应层）"""
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        if len(color) == 4:
            pygame.draw.rect(surf, color, pygame.Rect(0, 0, *rect.size), width)
        else:
            pygame.draw.rect(surf, color, pygame.Rect(0, 0, *rect.size), width)
        self._get_or_create(layer).add(surf, rect.topleft)

    def end(self):
        """帧末：按层 Z 序依次 blit 到屏幕，然后刷新"""
        for z in sorted(self._layers.keys()):
            self._layers[z].flush_to(self._screen)
        pygame.display.flip()

    def clear_layer(self, layer: int):
        if layer in self._layers:
            self._layers[layer].clear()

    def set_bg_color(self, color: tuple):
        self._bg_color = color

    @property
    def screen(self) -> pygame.Surface:
        return self._screen

    @property
    def screen_size(self) -> tuple[int, int]:
        return (SCREEN_WIDTH, SCREEN_HEIGHT)
