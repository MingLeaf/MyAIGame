# =============================================================
# items/item_base.py —— 物品基类
#
# 所有游戏物品（武器/护甲/消耗品）均继承自 Item。
# Item 本身只定义元数据；具体效果由子类实现。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ItemType(Enum):
    WEAPON     = "weapon"      # 武器
    ARMOR      = "armor"       # 护甲
    CONSUMABLE = "consumable"  # 消耗品
    MISC       = "misc"        # 杂项


@dataclass
class Item:
    """
    物品基类。

    字段说明：
        item_id     : 唯一字符串 ID，用于 item_database 注册 / 存档
        name        : 中文显示名称
        description : 物品描述文本（背包悬停时显示）
        icon_id     : 图标标识符（预留，对应 sprite sheet 的格子索引）
        weight      : 重量（kg），影响装备负重率
        stackable   : 是否可叠加（消耗品为 True）
        max_stack   : 最大叠加数量（stackable=True 时有效）
        item_type   : 物品类型枚举
    """
    item_id:     str      = "unknown"
    name:        str      = "未知物品"
    description: str      = ""
    icon_id:     int      = 0          # 预留图标索引
    weight:      float    = 0.0        # kg
    stackable:   bool     = False
    max_stack:   int      = 1
    item_type:   ItemType = ItemType.MISC

    def use(self, player) -> bool:
        """
        使用物品（消耗品子类覆盖此方法）。
        返回 True 表示使用成功（可消耗一次）。
        """
        return False

    def get_tooltip_lines(self) -> list[str]:
        """
        返回背包悬停提示的多行文本列表。
        子类可覆盖以追加额外属性行。
        """
        lines = [
            self.name,
            f"重量: {self.weight:.1f} kg",
        ]
        if self.description:
            lines.append(self.description)
        return lines

    def __repr__(self) -> str:
        return f"<Item [{self.item_id}] {self.name}>"
