# =============================================================
# map/collision_map.py —— 碰撞地图（静态碰撞检测）
# =============================================================

from __future__ import annotations
from typing import List, Tuple, Optional
import pygame

from map.tile import TileType, get_tile_props
from map.tile_map import TileMap


class CollisionMap:
    """
    基于瓦片地图构建的静态碰撞系统。
    提供：
    - AABB 与实心瓦片的碰撞查询
    - 单向平台检测
    - 坏损伤瓦片查询
    """

    def __init__(self, tile_map: TileMap):
        self._tm = tile_map

    # -------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------

    def get_solid_tiles_in_rect(self, rect: pygame.Rect) -> List[pygame.Rect]:
        """
        返回与给定矩形重叠的所有实心瓦片的世界坐标矩形列表。
        """
        ts = self._tm.tile_size
        col_start = max(0, rect.left  // ts)
        col_end   = min(self._tm.width,  rect.right  // ts + 1)
        row_start = max(0, rect.top   // ts)
        row_end   = min(self._tm.height, rect.bottom // ts + 1)

        result: List[pygame.Rect] = []
        for layer in self._tm.layers:
            if layer.layer_type not in ("ground",):
                continue
            for row in range(row_start, row_end):
                for col in range(col_start, col_end):
                    tid = layer.get(col, row)
                    props = get_tile_props(tid)
                    if props.solid:
                        result.append(self._tm.tile_rect(col, row))
        return result

    def get_platform_tiles_in_rect(self, rect: pygame.Rect) -> List[pygame.Rect]:
        """
        返回与给定矩形重叠的所有单向平台瓦片的世界坐标矩形列表。
        """
        ts = self._tm.tile_size
        col_start = max(0, rect.left  // ts)
        col_end   = min(self._tm.width,  rect.right  // ts + 1)
        row_start = max(0, rect.top   // ts)
        row_end   = min(self._tm.height, rect.bottom // ts + 1)

        result: List[pygame.Rect] = []
        for layer in self._tm.layers:
            if layer.layer_type not in ("ground",):
                continue
            for row in range(row_start, row_end):
                for col in range(col_start, col_end):
                    tid = layer.get(col, row)
                    props = get_tile_props(tid)
                    if props.one_way:
                        result.append(self._tm.tile_rect(col, row))
        return result

    def get_damage_tiles_in_rect(self, rect: pygame.Rect) -> List[Tuple[pygame.Rect, int, str]]:
        """
        返回与矩形重叠的伤害瓦片列表：[(tile_rect, damage, damage_type), ...]
        """
        ts = self._tm.tile_size
        col_start = max(0, rect.left  // ts)
        col_end   = min(self._tm.width,  rect.right  // ts + 1)
        row_start = max(0, rect.top   // ts)
        row_end   = min(self._tm.height, rect.bottom // ts + 1)

        result = []
        for layer in self._tm.layers:
            if layer.layer_type not in ("ground",):
                continue
            for row in range(row_start, row_end):
                for col in range(col_start, col_end):
                    tid = layer.get(col, row)
                    props = get_tile_props(tid)
                    if props.damage > 0:
                        result.append((
                            self._tm.tile_rect(col, row),
                            props.damage,
                            props.damage_type
                        ))
        return result

    def is_on_ground(self, rect: pygame.Rect) -> bool:
        """
        判断矩形底部是否紧贴实心地面（检测底部以下 2px）。
        """
        check = pygame.Rect(rect.left + 2, rect.bottom,
                            rect.width - 4, 2)
        tiles = self.get_solid_tiles_in_rect(check)
        if tiles:
            return True
        # 也检测单向平台
        platforms = self.get_platform_tiles_in_rect(check)
        return bool(platforms)

    def is_solid_at(self, wx: float, wy: float) -> bool:
        """判断某个世界坐标点是否在实心瓦片内"""
        col = int(wx // self._tm.tile_size)
        row = int(wy // self._tm.tile_size)
        for layer in self._tm.layers:
            if layer.layer_type == "ground":
                props = get_tile_props(layer.get(col, row))
                if props.solid:
                    return True
        return False
