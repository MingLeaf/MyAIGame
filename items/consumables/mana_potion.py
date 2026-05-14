# =============================================================
# items/consumables/mana_potion.py —— 灵力药剂
# =============================================================
from __future__ import annotations
from dataclasses import dataclass

from items.consumable import ConsumableItem, ConsumableEffect


@dataclass
class ManaPotion(ConsumableItem):
    """灵力（mana）恢复型消耗品。"""

    def __post_init__(self):
        super().__post_init__()
        self.effect = ConsumableEffect.RESTORE_MP

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 灵力药剂"]
        lines.append(f"回复 灵力: +{self.effect_value}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["ManaPotion"]
