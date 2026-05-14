# =============================================================
# map/tile.py —— 单个瓦片类（类型 / 碰撞 / 前景遮挡 / 特效）
# =============================================================

from __future__ import annotations
from enum import IntEnum
from typing import Optional
import pygame


class TileType(IntEnum):
    EMPTY       = 0   # 空气，无碰撞
    GROUND      = 1   # 实心地面，四面碰撞
    PLATFORM    = 2   # 单向跳跃平台，仅顶部碰撞
    WALL        = 3   # 实心墙壁（与 GROUND 相同，语义区分）
    DECORATION  = 4   # 纯视觉装饰，无碰撞
    SPIKE       = 5   # 尖刺，触碰持续扣血
    LAVA        = 6   # 熔岩，触碰触发燃烧
    WATER       = 7   # 水面，减速
    FOREGROUND  = 8   # 前景遮挡层（玩家走在其"后面"）
    LADDER      = 9   # 梯子，可攀爬


# -------------------------------------------------------
# 瓦片属性表（tile_id → TileProperties）
# -------------------------------------------------------

class TileProperties:
    """描述某个 tile_id 的静态属性"""

    def __init__(self,
                 tile_type: TileType = TileType.EMPTY,
                 solid: bool = False,
                 one_way: bool = False,
                 is_foreground: bool = False,
                 damage: int = 0,
                 damage_type: str = "",
                 color: tuple = (100, 100, 100)):
        self.tile_type    = tile_type
        self.solid        = solid       # 四面实心碰撞
        self.one_way      = one_way     # 仅顶部碰撞（平台）
        self.is_foreground= is_foreground
        self.damage       = damage      # 每秒伤害（0=无）
        self.damage_type  = damage_type
        self.color        = color       # 无素材时用于占位渲染


# 默认内置属性表（tile_id → TileProperties）
DEFAULT_TILE_PROPS: dict = {
    TileType.EMPTY:      TileProperties(TileType.EMPTY,     solid=False, color=(30, 30, 45)),
    TileType.GROUND:     TileProperties(TileType.GROUND,    solid=True,  color=(90, 75, 60)),
    TileType.PLATFORM:   TileProperties(TileType.PLATFORM,  solid=False, one_way=True, color=(120, 95, 70)),
    TileType.WALL:       TileProperties(TileType.WALL,      solid=True,  color=(70, 65, 60)),
    TileType.DECORATION: TileProperties(TileType.DECORATION,solid=False, color=(80, 100, 70)),
    TileType.SPIKE:      TileProperties(TileType.SPIKE,     solid=True,  damage=20, damage_type="physical", color=(180, 160, 140)),
    TileType.LAVA:       TileProperties(TileType.LAVA,      solid=False, damage=15, damage_type="fire",     color=(220, 80, 20)),
    TileType.WATER:      TileProperties(TileType.WATER,     solid=False, color=(40, 80, 160)),
    TileType.FOREGROUND: TileProperties(TileType.FOREGROUND,solid=False, is_foreground=True, color=(50, 70, 40)),
    TileType.LADDER:     TileProperties(TileType.LADDER,    solid=False, color=(140, 100, 60)),
}


def get_tile_props(tile_id: int) -> TileProperties:
    """根据 tile_id 获取属性，未知 ID 返回 EMPTY"""
    return DEFAULT_TILE_PROPS.get(tile_id, DEFAULT_TILE_PROPS[TileType.EMPTY])
