# =============================================================
# items/consumables/heal_potion.py —— HP 恢复药剂
#
# 适用：草药汤 / 高级圣水 等回复 HP 的消耗品。
# 实例化方式：
#   HealPotion(item_id="heal_potion_small", name="草药汤",
#              effect_value=30, max_stack=10, weight=0.2)
#
# 使用效果：
#   调用 player.stats.heal(effect_value)，复用基类 ConsumableItem.use()。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field

from items.consumable import ConsumableItem, ConsumableEffect


@dataclass
class HealPotion(ConsumableItem):
    """HP 恢复型消耗品。"""

    # 子类不再新增字段（complete 复用 ConsumableItem.effect_value），
    # 保持 dataclass 层级简洁，避免 init 顺序问题。
    def __post_init__(self):
        super().__post_init__()
        # 强制效果类型为 HEAL（即使 JSON 误填也修正）
        self.effect = ConsumableEffect.HEAL

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 治疗药剂"]
        lines.append(f"回复 HP: +{self.effect_value}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["HealPotion"]
