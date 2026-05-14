# =============================================================
# entities/player/player_inventory.py —— 玩家背包模块（包装层）
#
# 按工程文档命名规范暴露 PlayerInventory 类，
# 实际实现复用 player.inventory.Inventory（保持向后兼容）。
#
# 推荐导入：
#     from entities.player.player_inventory import PlayerInventory
#
# 旧路径仍然可用：
#     from player.inventory import Inventory
# =============================================================
from __future__ import annotations

from player.inventory import Inventory, InventorySlot, MAX_SLOTS


# 语义化别名
PlayerInventory = Inventory


__all__ = [
    "PlayerInventory",
    "Inventory",
    "InventorySlot",
    "MAX_SLOTS",
]
