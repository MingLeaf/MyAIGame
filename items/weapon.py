# =============================================================
# items/weapon.py —— 武器物品
#
# WeaponItem 是物品层（背包/装备栏）的武器表示。
# 它持有一个 weapons.base_weapon.BaseWeapon 实例，
# 装备时将该实例注入 player.weapon。
#
# 物理攻击力公式（game_rule.md §2.3）：
#   total_atk = base_atk + STR加成(重武器) or DEX加成(轻武器)
#   由 GrowthStats.get_atk_bonus(weapon) 计算，装备后自动同步。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from items.item_base import Item, ItemType

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from weapons.base_weapon import BaseWeapon


@dataclass
class WeaponItem(Item):
    """
    武器物品。

    额外字段：
        base_atk    : 武器基础物理攻击力
        str_scale   : 力量比例加成系数（大剑/战斧用）
        dex_scale   : 敏捷比例加成系数（匕首/弓用）
        weapon_art  : 武器技能名称（预留，中文）
        weapon_obj  : 对应的 BaseWeapon 实例（战斗逻辑用）

    注意：
        装备该武器时，Equipment 会执行：
            player.weapon = self.weapon_obj
            player.stats.apply_growth(player.growth, self.weapon_obj)
    """
    base_atk:   int    = 0
    str_scale:  float  = 0.0      # 大剑/战斧：力量加成系数
    dex_scale:  float  = 0.0      # 匕首/弓：敏捷加成系数
    weapon_art: str    = "普通攻击"
    weapon_obj: "BaseWeapon | None" = field(default=None, repr=False)

    # 固定物品类型
    item_type: ItemType = field(default=ItemType.WEAPON, init=False)

    def __post_init__(self):
        self.stackable = False
        self.max_stack = 1

    def get_tooltip_lines(self) -> list[str]:
        lines = [
            self.name,
            f"类型: 武器",
            f"基础攻击: {self.base_atk}",
        ]
        if self.str_scale > 0:
            lines.append(f"力量加成: ×{self.str_scale:.1f}")
        if self.dex_scale > 0:
            lines.append(f"敏捷加成: ×{self.dex_scale:.1f}")
        lines.append(f"武器技: {self.weapon_art}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines
