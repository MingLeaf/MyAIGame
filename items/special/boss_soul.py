# =============================================================
# items/special/boss_soul.py —— 灵核（Boss 掉落核心）
#
# Boss 死亡后必掉的特殊物品。
# 玩家可在营地处消耗，换取灵魂数 / 解锁专属技能。
# 第 6 阶段只完成数据 + 使用入口，奖励规则由后续 progression_system
# 通过订阅 "boss_soul_consumed" 事件实现。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from items.item_base import Item, ItemType
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class BossSoul(Item):
    """灵核。"""

    boss_id:    str = ""
    soul_value: int = 100      # 消耗后获得的灵魂数

    item_type: ItemType = field(default=ItemType.MISC, init=False)

    def __post_init__(self):
        self.stackable = False
        self.max_stack = 1

    def use(self, player: "Player") -> bool:
        event_manager.emit("boss_soul_consumed", {
            "boss_id":    self.boss_id,
            "soul_value": self.soul_value,
            "item_id":    self.item_id,
            "player":     player,
        })
        event_manager.emit("item_used", {
            "item_id": self.item_id,
            "effect":  "boss_soul",
            "value":   self.soul_value,
        })
        return True

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 灵核（Boss 之魂）"]
        lines.append(f"灵魂值: {self.soul_value}")
        if self.boss_id:
            lines.append(f"来源: {self.boss_id}")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["BossSoul"]
