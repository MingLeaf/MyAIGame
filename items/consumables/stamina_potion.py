# =============================================================
# items/consumables/stamina_potion.py —— 精力（耐力）饮剂
#
# 注意：基类 ConsumableEffect 没有专门的 RESTORE_STAMINA 类型，
#       这里用 CUSTOM 路径，直接操作 player.stats.stamina。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from items.consumable import ConsumableItem, ConsumableEffect
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class StaminaPotion(ConsumableItem):
    """耐力恢复型消耗品（精力饮剂）。"""

    def __post_init__(self):
        super().__post_init__()
        self.effect = ConsumableEffect.CUSTOM

    def use(self, player: "Player") -> bool:
        stats = getattr(player, "stats", None)
        if stats is None:
            return False
        amount = float(self.effect_value)
        if amount <= 0:
            return False
        before = stats.stamina
        stats.stamina = min(stats.max_stamina, stats.stamina + amount)
        gained = stats.stamina - before
        event_manager.emit("item_used", {
            "item_id": self.item_id,
            "effect": "restore_stamina",
            "value": gained,
        })
        return True

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 精力饮剂"]
        lines.append(f"回复 耐力: +{self.effect_value}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["StaminaPotion"]
