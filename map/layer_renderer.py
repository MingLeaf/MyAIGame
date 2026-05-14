# =============================================================
# map/layer_renderer.py —— 分层渲染器（背景/地面/实体/前景遮挡）
# =============================================================

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple
import pygame

if TYPE_CHECKING:
    from map.tile_map import TileMap
    from core.renderer import Renderer
    from core.camera import Camera

from config import (LAYER_BACKGROUND, LAYER_GROUND,
                    LAYER_ENTITY, LAYER_FOREGROUND,
                    SCREEN_WIDTH, SCREEN_HEIGHT)


class LayerRenderer:
    """
    将瓦片地图各层按照正确 Z 序提交给 Renderer 的渲染器。

    渲染顺序：
        LAYER_BACKGROUND  → 地图背景层
        LAYER_GROUND      → 地图地面层（实体在其上方）
        LAYER_ENTITY      → 游戏实体（由各实体自行提交）
        LAYER_FOREGROUND  → 前景遮挡层
    """

    def __init__(self, tile_map: "TileMap"):
        self._tm = tile_map

    def render(self, renderer: "Renderer", camera: "Camera"):
        screen_w, screen_h = renderer.screen_size
        cam_offset: Tuple[int, int] = camera.apply_offset()
        surf = renderer.screen   # 直接绘制到屏幕（瓦片层不走分层队列）

        # 背景层
        self._tm.render_layer(surf, "background", cam_offset,
                              screen_w, screen_h)
        # 地面层
        self._tm.render_layer(surf, "ground", cam_offset,
                              screen_w, screen_h)

    def render_foreground(self, renderer: "Renderer", camera: "Camera"):
        """前景遮挡层，在实体渲染完成后调用"""
        screen_w, screen_h = renderer.screen_size
        cam_offset: Tuple[int, int] = camera.apply_offset()
        surf = renderer.screen
        self._tm.render_layer(surf, "foreground", cam_offset,
                              screen_w, screen_h)
