# =============================================================
# systems/loot_system.py —— 全局掉落计算系统
# =============================================================
#
# 第 7 阶段：取代 combat/drop_system.py 中分散在敌人类的
# drop_table 硬编码方案，将所有掉落表迁到 data/balance/loot_tables.json，
# 并提供统一查询/掷骰入口。
#
# 调用方式：
#   from systems.loot_system import LootSystem
#   table = LootSystem.get_table("infantry_basic")
#   results = LootSystem.roll(table)            # [(item_id, qty), ...]
#   LootSystem.spawn(area, x, y, "infantry_basic")  # 直接掷骰并落地
#
# 兼容性：
#   - 仍接受 List[DropEntry] 与现有 ItemManager.roll_and_spawn 互通
#   - 旧敌人类设置 drop_table 的方式继续生效（与新表共存）
# =============================================================
from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

from combat.drop_system import DropEntry, roll_drops
from entities.enemy.types._data_loader import build_drop_table

if TYPE_CHECKING:
    from map.area import Area


class LootSystem:
    """全局掉落入口（无状态，全部 staticmethod）。"""

    # ----------------------------------------------------------------
    # 表查询
    # ----------------------------------------------------------------

    @staticmethod
    def get_table(loot_id: str) -> List[DropEntry]:
        """根据掉落表 ID 返回 List[DropEntry]（带缓存）。"""
        return build_drop_table(loot_id)

    # ----------------------------------------------------------------
    # 掷骰
    # ----------------------------------------------------------------

    @staticmethod
    def roll(table_or_id) -> List[Tuple[str, int]]:
        """
        对掉落表掷骰。
        :param table_or_id: 既接受 loot_id 字符串，也接受 List[DropEntry]
        :return: [(item_id, quantity), ...] 仅含命中项
        """
        if isinstance(table_or_id, str):
            table = LootSystem.get_table(table_or_id)
        else:
            table = table_or_id
        return roll_drops(table)

    # ----------------------------------------------------------------
    # 直接生成到地面
    # ----------------------------------------------------------------

    @staticmethod
    def spawn(area: "Area", x: float, y: float, table_or_id) -> list:
        """
        掷骰 + 在 area 上生成 DroppedItem。
        :return: 新建的 DroppedItem 列表
        """
        from items.item_manager import ItemManager
        if isinstance(table_or_id, str):
            table = LootSystem.get_table(table_or_id)
        else:
            table = table_or_id
        return ItemManager.roll_and_spawn(area, x, y, table)

    # ----------------------------------------------------------------
    # 敌人专用：综合 enemy.drop_table（实例字段）+ 全局表
    # ----------------------------------------------------------------

    @staticmethod
    def spawn_for_enemy(area: "Area", enemy) -> list:
        """
        给指定敌人执行掉落。
        - 优先使用 enemy.drop_table（已由 types/_data_loader 灌入全局表内容）
        - 兜底：尝试根据 enemy.CATEGORY 查全局表
        """
        if area is None or enemy is None:
            return []
        wx = enemy.rect.centerx
        wy = enemy.rect.top
        table = getattr(enemy, "drop_table", None)
        if not table:
            cat = getattr(enemy, "CATEGORY", None)
            if cat is None:
                return []
            from entities.enemy.types._data_loader import get_loot_table_for
            table = get_loot_table_for(cat)
        return LootSystem.spawn(area, wx, wy, table)


__all__ = ["LootSystem"]
