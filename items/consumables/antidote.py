# =============================================================
# items/consumables/antidote.py —— 万能解药
#
# 清除所有可解除的状态异常（中毒/流血/燃烧/诅咒/眩晕等）。
# 冰冻不在此清除范围（冰冻一般通过翻滚或热源化解）。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple

from items.consumable import ConsumableItem, ConsumableEffect
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


# 可被解药清除的状态名集合（与 combat.status_effect 中的 name 对应）
_CURABLE_STATUS: Tuple[str, ...] = ("poison", "toxic", "bleed", "burn", "curse", "stun")


@dataclass
class Antidote(ConsumableItem):
    """万能解药 —— 清除多种状态异常。"""

    def __post_init__(self):
        super().__post_init__()
        self.effect = ConsumableEffect.CUSTOM

    def use(self, player: "Player") -> bool:
        status = getattr(player, "status", None)
        cleared = []
        if status is not None:
            for name in _CURABLE_STATUS:
                if status.has(name):
                    status.remove(name)
                    cleared.append(name)
        # 即使无状态可清也消耗（与魂系一致）
        event_manager.emit("item_used", {
            "item_id": self.item_id,
            "effect": "antidote",
            "cleared": cleared,
        })
        return True

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 解药"]
        lines.append("效果: 清除所有状态异常")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["Antidote", "_CURABLE_STATUS"]
