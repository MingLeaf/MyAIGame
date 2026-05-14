# =============================================================
# entities/enemy/types/_data_loader.py —— 敌人数据加载工具
# =============================================================
#
# 提供 load_enemy_data(category) 读取 data/entities/enemies/<id>.json
# 并解析为 EnemyStats / 渲染参数 / 战斗参数。
#
# 同时提供 build_drop_table(loot_id) 从 data/balance/loot_tables.json
# 读取并转换为 List[DropEntry]。
# =============================================================
from __future__ import annotations

from typing import Dict, Any, List, Tuple
from utils import json_loader
from entities.enemy.enemy_stats import EnemyStats
from combat.drop_system import DropEntry


# ----------------------------------------------------------------
# 单类敌人数据
# ----------------------------------------------------------------

_ENEMY_CACHE: Dict[str, Dict[str, Any]] = {}


def load_enemy_data(category: str) -> Dict[str, Any]:
    """
    从 data/entities/enemies/<category>.json 加载敌人完整数据。
    缓存到内存，重复调用不会重复读盘。
    缺失文件则返回空 dict（调用方自行兜底）。
    """
    if category in _ENEMY_CACHE:
        return _ENEMY_CACHE[category]
    try:
        data = json_loader.load_from_data_dir(f"entities/enemies/{category}.json")
    except FileNotFoundError:
        data = {}
    _ENEMY_CACHE[category] = data
    return data


def build_stats(category: str) -> EnemyStats:
    """直接读 JSON 并返回构造好的 EnemyStats。"""
    data = load_enemy_data(category)
    stats_dict = data.get("stats", {})
    return EnemyStats.from_dict(stats_dict)


def get_render_params(category: str) -> Tuple[int, int, tuple]:
    """返回 (width, height, color)。"""
    data = load_enemy_data(category)
    r = data.get("render", {})
    w = int(r.get("width",  24))
    h = int(r.get("height", 48))
    color = tuple(r.get("color", [120, 200, 80]))
    return w, h, color


# ----------------------------------------------------------------
# 掉落表
# ----------------------------------------------------------------

_LOOT_CACHE: Dict[str, List[DropEntry]] = {}
_LOOT_RAW: Dict[str, list] = {}
_LOOT_LOADED: bool = False


def _ensure_loot_loaded() -> None:
    global _LOOT_LOADED, _LOOT_RAW
    if _LOOT_LOADED:
        return
    try:
        raw = json_loader.load_from_data_dir("balance/loot_tables.json")
    except FileNotFoundError:
        raw = {}
    # 过滤掉 _comment 之类的元字段
    _LOOT_RAW = {k: v for k, v in raw.items() if not k.startswith("_")}
    _LOOT_LOADED = True


def build_drop_table(loot_id: str) -> List[DropEntry]:
    """
    根据掉落表 ID 读取 data/balance/loot_tables.json 中的 entry 数组，
    返回组装好的 List[DropEntry]。
    """
    _ensure_loot_loaded()

    if loot_id in _LOOT_CACHE:
        return _LOOT_CACHE[loot_id]

    raw_entries = _LOOT_RAW.get(loot_id, [])
    table: List[DropEntry] = []
    for entry in raw_entries:
        try:
            table.append(DropEntry(
                item_id = entry["item_id"],
                chance  = float(entry.get("chance", 1.0)),
                qty_min = int(entry.get("qty_min", 1)),
                qty_max = int(entry.get("qty_max", 1)),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    _LOOT_CACHE[loot_id] = table
    return table


def get_loot_table_for(category: str) -> List[DropEntry]:
    """根据敌人 category 读取 .loot_table 字段，再去全局表里查。"""
    data = load_enemy_data(category)
    loot_id = data.get("loot_table", "")
    if not loot_id:
        return []
    return build_drop_table(loot_id)


# ----------------------------------------------------------------
# 测试 / 重载
# ----------------------------------------------------------------

def clear_caches() -> None:
    _ENEMY_CACHE.clear()
    _LOOT_CACHE.clear()
    global _LOOT_LOADED, _LOOT_RAW
    _LOOT_LOADED = False
    _LOOT_RAW = {}


__all__ = [
    "load_enemy_data", "build_stats", "get_render_params",
    "build_drop_table", "get_loot_table_for", "clear_caches",
]
