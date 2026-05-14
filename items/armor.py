# =============================================================
# items/armor.py —— 护甲物品
#
# 护甲分 4 个部位：头盔/胸甲/手甲/腿甲。
# 每件护甲提供防御值（DEF）和韧性（poise）。
#
# 防御计算（game_rule.md §2.3）：
#   damage_received = max(1, raw_damage - total_DEF)
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from items.item_base import Item, ItemType


class ArmorSlot(Enum):
    """护甲槽位枚举，与 Equipment 的槽位键对应"""
    HEAD  = "head"
    CHEST = "chest"
    HANDS = "hands"
    LEGS  = "legs"


@dataclass
class ArmorItem(Item):
    """
    护甲物品。

    额外字段：
        slot        : 护甲槽位（ArmorSlot 枚举）
        defense     : 物理防御值（减伤量，固定值）
        poise       : 韧性值（承受攻击后硬直抵抗）
        fire_res    : 火焰抗性（0~100，百分比）
        magic_res   : 魔法抗性（0~100）
        holy_res    : 神圣抗性（0~100）
    """
    slot:      ArmorSlot = ArmorSlot.CHEST
    defense:   int       = 0
    poise:     float     = 0.0
    fire_res:  int       = 0       # 火焰抗性 %
    magic_res: int       = 0       # 魔法抗性 %
    holy_res:  int       = 0       # 神圣抗性 %
    set_id:    str       = ""      # 套装ID（与 items/equipment/set_bonus.py 配合）

    # 固定物品类型
    item_type: ItemType = field(default=ItemType.ARMOR, init=False)

    _SLOT_NAMES = {
        ArmorSlot.HEAD:  "头盔",
        ArmorSlot.CHEST: "胸甲",
        ArmorSlot.HANDS: "手甲",
        ArmorSlot.LEGS:  "腿甲",
    }

    def __post_init__(self):
        self.stackable = False
        self.max_stack = 1

    def get_tooltip_lines(self) -> list[str]:
        slot_name = self._SLOT_NAMES.get(self.slot, "护甲")
        lines = [
            self.name,
            f"类型: {slot_name}",
            f"防御: {self.defense}",
            f"韧性: {self.poise:.0f}",
        ]
        if self.fire_res:
            lines.append(f"火焰抗性: {self.fire_res}%")
        if self.magic_res:
            lines.append(f"魔法抗性: {self.magic_res}%")
        if self.holy_res:
            lines.append(f"神圣抗性: {self.holy_res}%")
        if self.set_id:
            lines.append(f"套装: {self.set_id}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines
