# =============================================================
# entities/enemy/enemy_spawner.py —— 敌人生成器（数据驱动）
# =============================================================
#
# 职责：
#   - 从 data/maps/<area_id>/enemy_spawns.json 读取生成配置
#   - 也支持直接传入 spawn 列表（区域 tilemap.json 内 enemy_spawns 字段）
#   - 通过 entities.enemy.types.create_enemy(category, x, y) 实例化
#   - 应用可选 level 缩放（HP/ATK 倍率）
#
# spawn 配置项：
#   {
#     "type":  "infantry",       # 必填，对应 ENEMY_REGISTRY
#     "x":     15,               # 瓦片坐标 X
#     "y":     17,               # 瓦片坐标 Y（脚底所在行）
#     "level": 1,                # 可选，等级，影响 HP/ATK 缩放
#     "patrol_radius": 96.0      # 可选，覆盖默认巡逻半径
#   }
# =============================================================
from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

from utils import json_loader
from entities.enemy.types import create_enemy, ENEMY_REGISTRY


# 等级缩放：每级 HP +20%, ATK +12%（线性，温和）
LEVEL_HP_MUL  = 0.20
LEVEL_ATK_MUL = 0.12


def _scale_by_level(enemy, level: int) -> None:
    if level <= 1:
        return
    delta = level - 1
    new_max_hp = int(enemy.stats.max_hp * (1.0 + LEVEL_HP_MUL * delta))
    enemy.stats.max_hp = new_max_hp
    enemy.stats.hp     = new_max_hp
    enemy.stats.atk    = int(enemy.stats.atk * (1.0 + LEVEL_ATK_MUL * delta))


def spawn_from_config(area, spawn_list: List[Dict[str, Any]]) -> List:
    """
    根据 spawn 配置列表为给定 area 生成敌人。
    自动按 area.tile_map.tile_size 把瓦片坐标转换为像素坐标。
    返回新建的 enemy 列表（同时已 append 到 area.enemies）。
    """
    if area is None or not spawn_list:
        return []

    ts = getattr(area.tile_map, "tile_size", 32)
    spawned: List = []

    for cfg in spawn_list:
        kind = str(cfg.get("type", "infantry")).lower()
        if kind not in ENEMY_REGISTRY:
            # 未知类型 → 兜底为 infantry
            kind = "infantry"

        wx = cfg.get("x", 0) * ts + ts // 2
        # 让脚底贴在 (y+1) 行的顶部（原 area._load_enemies 行为一致）
        wy = cfg.get("y", 0) * ts + ts

        enemy = create_enemy(kind, float(wx), float(wy))

        # 可选覆盖：巡逻半径
        if "patrol_radius" in cfg:
            try:
                enemy.stats.patrol_radius = float(cfg["patrol_radius"])
            except (TypeError, ValueError):
                pass

        # 等级缩放
        level = int(cfg.get("level", 1))
        _scale_by_level(enemy, level)

        area.enemies.append(enemy)
        spawned.append(enemy)

    return spawned


def spawn_from_file(area, file_path: str) -> List:
    """
    从绝对路径加载 enemy_spawns.json 并生成敌人。
    JSON 结构：{ "spawns": [ ...spawn config... ] }
    或直接 [ ...spawn config... ]（顶层是数组）
    """
    if not os.path.isfile(file_path):
        return []
    raw = json_loader.load(file_path)
    spawn_list = raw.get("spawns") if isinstance(raw, dict) else raw
    if not isinstance(spawn_list, list):
        return []
    return spawn_from_config(area, spawn_list)


def spawn_from_area_file(area, area_id: str) -> List:
    """
    从 data/maps/<area_id>/enemy_spawns.json 加载并生成。
    若文件不存在则回退到 area.tile_map.objects['enemy_spawns']。
    返回新建的 enemy 列表。
    """
    if area is None:
        return []
    try:
        raw = json_loader.load_from_data_dir(f"maps/{area_id}/enemy_spawns.json")
    except FileNotFoundError:
        raw = None

    if raw is not None:
        spawn_list = raw.get("spawns") if isinstance(raw, dict) else raw
        if isinstance(spawn_list, list):
            return spawn_from_config(area, spawn_list)

    # 回退：使用 tilemap.json 内置的 enemy_spawns
    fallback = area.tile_map.objects.get("enemy_spawns", [])
    if isinstance(fallback, list):
        return spawn_from_config(area, fallback)
    return []


__all__ = [
    "spawn_from_config", "spawn_from_file", "spawn_from_area_file",
]
