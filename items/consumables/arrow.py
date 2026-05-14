# =============================================================
# items/consumables/arrow.py —— 箭矢（弓的弹药）
#
# 关键约定：
#   - item_id 必须是 "arrow"，与 weapons/types/bow.py 中
#     ARROW_ITEM_ID 严格对应。
#   - 不可直接"使用"，由 weapons.types.bow.Bow 在攻击 / 战技时
#     通过 inventory.remove_item_id("arrow", 1) 消耗。
#   - 默认 max_stack=99，便于囤积。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from items.consumable import ConsumableItem, ConsumableEffect

if TYPE_CHECKING:
    from entities.player.player import Player


# 与 weapons/types/bow.py 的 ARROW_ITEM_ID 必须一致
ARROW_ITEM_ID = "arrow"


@dataclass
class ArrowItem(ConsumableItem):
    """
    箭矢消耗品（弓的弹药）。

    注意：此物品不响应背包"使用"操作，
          仅由 Bow 在攻击 / BowPiercingArrowArt 在战技时消耗。
    """

    def __post_init__(self):
        super().__post_init__()
        self.effect = ConsumableEffect.CUSTOM
        self.stackable = True
        if self.max_stack <= 1:
            self.max_stack = 99
        # 强制 item_id（兜底）
        if not self.item_id or self.item_id == "unknown":
            self.item_id = ARROW_ITEM_ID

    def use(self, player: "Player") -> bool:
        # 从背包直接"使用"无效，必须由弓武器消耗。
        return False

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 弹药 (弓)"]
        lines.append(f"重量: {self.weight:.2f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["ArrowItem", "ARROW_ITEM_ID"]
