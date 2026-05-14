# =============================================================
# combat/drop_system.py —— 敌人死亡掉落系统
#
# 设计：
#   - 每个敌人子类拥有 drop_table: list[DropEntry]
#   - BaseEnemy 提供 roll_drops() 方法
#   - GameScene 监听 enemy_dead 事件，调用 roll_drops()
#     并将物品直接放入玩家背包，同时发送飘字提示
#
# DropEntry 字段：
#   item_id   : 物品 ID（对应 item_database 注册表）
#   chance    : 掉落概率 [0.0, 1.0]
#   qty_min   : 最小数量
#   qty_max   : 最大数量
# =============================================================
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class DropEntry:
    """单条掉落记录。"""
    item_id: str
    chance:  float = 1.0    # 掉落概率 0.0~1.0
    qty_min: int   = 1
    qty_max: int   = 1


def roll_drops(drop_table: List[DropEntry]) -> List[Tuple[str, int]]:
    """
    对掉落表进行随机掷骰。
    返回 [(item_id, quantity), ...] 的列表（只含实际触发的掉落）。
    """
    results = []
    for entry in drop_table:
        if random.random() <= entry.chance:
            qty = random.randint(entry.qty_min, entry.qty_max)
            results.append((entry.item_id, qty))
    return results


def apply_drops_to_player(
    drop_results: List[Tuple[str, int]],
    player: "Player",
) -> List[str]:
    """
    将掉落物品放入玩家背包。
    返回实际加入背包的物品名称列表（用于飘字提示）。
    """
    from items.item_database import item_db

    added_names = []
    for item_id, qty in drop_results:
        item = item_db.create(item_id)
        if item is None:
            continue
        inventory = getattr(player, "inventory", None)
        if inventory is None:
            continue
        ok, leftover = inventory.add(item, qty)
        if ok:
            added_names.append(f"{item.name}×{qty - leftover}")

        from core.event_manager import event_manager
        event_manager.emit("item_dropped", {
            "item_id": item_id,
            "quantity": qty,
            "player": player,
        })

    return added_names
