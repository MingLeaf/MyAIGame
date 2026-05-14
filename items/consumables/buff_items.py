# =============================================================
# items/consumables/buff_items.py —— 战斗增益消耗品
#
# 包含：锋刃石粉 / 圣油 / 烈焰松脂 / 铁皮膏 / 狂战药
#
# 实现策略：
#   暂时通过事件总线派发 "player_buff_applied" 事件；
#   完整 BuffManager 由后续阶段实现，此处只确保链路通畅。
#   使用后立即 emit "item_used" 与 "player_buff_applied"，
#   UI/特效 系统监听后即可显示飘字与图标。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from items.consumable import ConsumableItem, ConsumableEffect
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class BuffItem(ConsumableItem):
    """
    通用战斗增益消耗品。

    字段：
        buff_type      : buff 类型（如 "atk_bonus" / "def_bonus" /
                         "weapon_fire" / "weapon_holy" / "berserk"）
        buff_value     : 数值（百分比或固定加值，由 buff_type 决定）
        buff_duration  : 持续时间（秒）
        side_effect    : 可选的副作用 buff_type（如狂战药 def_down_0.20）
    """
    buff_type:     str   = "atk_bonus"
    buff_value:    float = 0.0
    buff_duration: float = 30.0
    side_effect:   str   = ""

    def __post_init__(self):
        super().__post_init__()
        self.effect = ConsumableEffect.CUSTOM

    def use(self, player: "Player") -> bool:
        # 主增益事件
        event_manager.emit("player_buff_applied", {
            "buff_type": self.buff_type,
            "value":     self.buff_value,
            "duration":  self.buff_duration,
            "item_id":   self.item_id,
            "player":    player,
        })
        # 副作用（如狂战药降防御）
        if self.side_effect:
            event_manager.emit("player_buff_applied", {
                "buff_type": self.side_effect,
                "value":     0.0,
                "duration":  self.buff_duration,
                "item_id":   self.item_id,
                "player":    player,
                "is_side":   True,
            })
        event_manager.emit("item_used", {
            "item_id": self.item_id,
            "effect":  "buff",
            "buff_type": self.buff_type,
            "value":   self.buff_value,
        })
        return True

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 强化药品"]
        lines.append(f"效果: {self.buff_type}  +{self.buff_value}")
        lines.append(f"持续: {self.buff_duration:.0f} 秒")
        if self.side_effect:
            lines.append(f"副作用: {self.side_effect}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["BuffItem"]
