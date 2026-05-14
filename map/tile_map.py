# =============================================================
# map/tile_map.py —— 瓦片地图（加载 JSON / 渲染）
# =============================================================

from __future__ import annotations
import os
from typing import List, Dict, Optional, Tuple
import pygame

from map.tile import TileType, TileProperties, get_tile_props
from utils import json_loader
from utils import resource_cache


class MapLayer:
    """地图的单个逻辑层"""

    def __init__(self, name: str, layer_type: str,
                 width: int, height: int, data: List[List[int]]):
        self.name        = name
        self.layer_type  = layer_type   # "background" / "ground" / "foreground"
        self.width       = width
        self.height      = height
        self.data        = data         # data[row][col]

    def get(self, col: int, row: int) -> int:
        """安全获取 tile_id，越界返回 0"""
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.data[row][col]
        return 0


class TileMap:
    """
    瓦片地图：
    - 从 JSON 文件加载多层地图数据
    - 渲染到 pygame.Surface（带摄像机偏移）
    - 提供碰撞层访问接口
    """

    def __init__(self):
        self.name      = ""
        self.tile_size = 32
        self.width     = 0    # 瓦片列数
        self.height    = 0    # 瓦片行数
        self.layers: List[MapLayer] = []
        self.objects: dict = {}

        # 素材：tileset surface（可为 None，回退到颜色绘制）
        self._tileset: Optional[pygame.Surface] = None
        self._tileset_cols = 0

        # 渲染缓存（每层预烘焙为静态 Surface）
        self._layer_cache: Dict[str, pygame.Surface] = {}

    # ---- 加载 ----

    def load(self, path: str):
        """从 JSON 文件加载地图数据"""
        data = json_loader.load(path)
        self.name      = data.get("name", "")
        self.tile_size = data.get("tile_size", 32)
        self.width     = data.get("width", 0)
        self.height    = data.get("height", 0)
        self.objects   = data.get("objects", {})

        self.layers.clear()
        for layer_data in data.get("layers", []):
            raw = layer_data.get("data", [])
            # 支持一维数组（自动折行）和二维数组
            if raw and isinstance(raw[0], list):
                grid = raw
            else:
                grid = [raw[i * self.width:(i + 1) * self.width]
                        for i in range(self.height)]
            layer = MapLayer(
                name       = layer_data.get("name", ""),
                layer_type = layer_data.get("type", "ground"),
                width      = self.width,
                height     = self.height,
                data       = grid,
            )
            self.layers.append(layer)

        # 尝试加载 tileset
        tileset_name = data.get("tileset", "")
        self._try_load_tileset(tileset_name)

        # 清除渲染缓存
        self._layer_cache.clear()

    def _try_load_tileset(self, tileset_name: str):
        if not tileset_name:
            return
        from config import ASSETS_DIR
        path = os.path.join(ASSETS_DIR, "tilesets", f"{tileset_name}_tileset.png")
        if os.path.isfile(path):
            self._tileset = resource_cache.load_image(path)
            # 假设 tileset 横向 16 列
            self._tileset_cols = self._tileset.get_width() // self.tile_size

    # ---- 渲染 ----

    def render_layer(self, surface: pygame.Surface,
                     layer_type: str,
                     camera_offset: Tuple[int, int],
                     screen_w: int,
                     screen_h: int):
        """
        渲染指定类型的所有层。
        camera_offset: (cam_x, cam_y) 世界坐标中摄像机左上角位置
        """
        ts = self.tile_size
        cam_x, cam_y = camera_offset

        # 视口内的瓦片范围
        col_start = max(0, cam_x // ts)
        col_end   = min(self.width,  (cam_x + screen_w) // ts + 2)
        row_start = max(0, cam_y // ts)
        row_end   = min(self.height, (cam_y + screen_h) // ts + 2)

        for layer in self.layers:
            if layer.layer_type != layer_type:
                continue
            for row in range(row_start, row_end):
                for col in range(col_start, col_end):
                    tile_id = layer.get(col, row)
                    if tile_id == TileType.EMPTY:
                        continue
                    sx = col * ts - cam_x
                    sy = row * ts - cam_y
                    self._draw_tile(surface, tile_id, sx, sy)

    def _draw_tile(self, surface: pygame.Surface,
                   tile_id: int, sx: int, sy: int):
        ts = self.tile_size
        dest = pygame.Rect(sx, sy, ts, ts)

        if self._tileset is not None:
            # 从 tileset 切割
            idx = tile_id - 1   # tileset 从 0 开始，tile_id 从 1 开始
            tx  = (idx % self._tileset_cols) * ts
            ty  = (idx // self._tileset_cols) * ts
            surface.blit(self._tileset, dest,
                         pygame.Rect(tx, ty, ts, ts))
        else:
            # 颜色占位
            props = get_tile_props(tile_id)
            pygame.draw.rect(surface, props.color, dest)
            # 绘制轻微边框增加层次感
            border_color = tuple(max(0, c - 20) for c in props.color)
            pygame.draw.rect(surface, border_color, dest, 1)

    # ---- 数据访问 ----

    def get_ground_layer(self) -> Optional[MapLayer]:
        """获取第一个 ground 类型的层（用于碰撞）"""
        for layer in self.layers:
            if layer.layer_type == "ground":
                return layer
        return None

    def get_tile_at_world(self, wx: float, wy: float,
                          layer_type: str = "ground") -> int:
        """
        根据世界坐标返回该位置的 tile_id（取第一个匹配层）
        """
        col = int(wx // self.tile_size)
        row = int(wy // self.tile_size)
        for layer in self.layers:
            if layer.layer_type == layer_type:
                return layer.get(col, row)
        return 0

    def tile_rect(self, col: int, row: int) -> pygame.Rect:
        """返回某个瓦片格的世界坐标矩形"""
        ts = self.tile_size
        return pygame.Rect(col * ts, row * ts, ts, ts)

    @property
    def world_width(self) -> int:
        return self.width * self.tile_size

    @property
    def world_height(self) -> int:
        return self.height * self.tile_size

    def get_spawn_point(self) -> Tuple[float, float]:
        """
        获取玩家出生点世界坐标。
        spawn JSON 中 (x, y) 为出生点所在瓦片列 / 行。
        返回值 y 为「该行顶部」—— 即玩家底部对齐到该行上边缘，
        确保玩家站在该行上方而非嵌入其中。
        """
        spawn = self.objects.get("player_spawn", {})
        ts = self.tile_size
        # x 取格子水平中心，y 取格子顶部（玩家底部对齐地面顶部）
        return (float(spawn.get("x", 6) * ts + ts // 2),
                float(spawn.get("y", 16) * ts))
