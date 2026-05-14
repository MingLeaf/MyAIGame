# =============================================================
# items/special/upgrade_material.py —— 武器强化材料
#
# 与第 5 阶段 weapons.weapon_upgrade.WeaponUpgrade 的 5 路线对应：
#   none / sharp / heavy / blessed / elemental
#
# tier 表示材料品阶（1~3），代表强化阶段：
#   tier 1：+1 ~ +4
#   tier 2：+5 ~ +7
#   tier 3：+8 ~ +10
#
# 实际强化时由铁匠 NPC / 营地强化菜单读取 player.inventory 中
# 对应 route+tier 的材料数量决定可强化等级。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from items.item_base import Item, ItemType

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class UpgradeMaterial(Item):
    """武器强化材料。"""

    route: str = "none"   # 路线（与 UpgradeRoute 一致）
    tier:  int = 1        # 品阶 1/2/3

    item_type: ItemType = field(default=ItemType.MISC, init=False)

    def __post_init__(self):
        self.stackable = True
        if self.max_stack <= 1:
            self.max_stack = 99

    def use(self, player: "Player") -> bool:
        # 强化材料不能直接使用，必须通过铁匠 / 强化菜单消耗
        return False

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 强化材料"]
        lines.append(f"路线: {self.route} / 品阶: T{self.tier}")
        lines.append(f"重量: {self.weight:.2f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["UpgradeMaterial"]
