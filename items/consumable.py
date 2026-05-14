# =============================================================
# items/consumable.py —— 消耗品
#
# 消耗品通过 use(player) 直接作用于玩家数值。
# 支持：回血（estus flask）/ 回蓝（蓝瓶）/ 解毒 / 自定义回调
#
# 用法：
#   item = item_db.get("estus_flask")
#   item.use(player)   # → player.stats.heal(60)
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING
from items.item_base import Item, ItemType

if TYPE_CHECKING:
    from entities.player.player import Player


# ---- 消耗品效果类型常量 ----
class ConsumableEffect:
    HEAL        = "heal"        # 回复 HP
    RESTORE_MP  = "restore_mp"  # 回复 Mana
    CURE_POISON = "cure_poison" # 解毒
    CUSTOM      = "custom"      # 自定义回调


@dataclass
class ConsumableItem(Item):
    """
    消耗品物品。

    额外字段：
        effect          : 效果类型（ConsumableEffect 中的常量字符串）
        effect_value    : 效果数值（治疗量、回蓝量等）
        use_callback    : 自定义回调（effect=CUSTOM 时使用）
                          签名：callback(player) -> bool

    叠加：
        stackable = True，max_stack = 20（默认）
    """
    effect:       str   = ConsumableEffect.HEAL
    effect_value: int   = 0
    use_callback: Optional[Callable] = field(default=None, repr=False)

    # 固定物品类型
    item_type: ItemType = field(default=ItemType.CONSUMABLE, init=False)

    def __post_init__(self):
        self.stackable = True
        if self.max_stack <= 1:
            self.max_stack = 20

    # ----------------------------------------------------------------
    # 使用接口
    # ----------------------------------------------------------------

    def use(self, player: "Player") -> bool:
        """
        使用消耗品，直接操作 player.stats。
        返回 True 表示使用成功（耗费一次）。
        """
        stats = player.stats

        if self.effect == ConsumableEffect.HEAL:
            healed = stats.heal(self.effect_value)
            if healed > 0:
                from core.event_manager import event_manager
                event_manager.emit("item_used", {
                    "item_id": self.item_id,
                    "effect": "heal",
                    "value": healed,
                })
            # 即使已满血也消耗（与魂系设计一致）
            return True

        elif self.effect == ConsumableEffect.RESTORE_MP:
            stats.restore_mana(self.effect_value)
            from core.event_manager import event_manager
            event_manager.emit("item_used", {
                "item_id": self.item_id,
                "effect": "restore_mp",
                "value": self.effect_value,
            })
            return True

        elif self.effect == ConsumableEffect.CURE_POISON:
            # 清除中毒状态（如果有状态管理器则清除）
            status_mgr = getattr(player, "status", None)
            if status_mgr is not None:
                status_mgr.remove("poison")
                status_mgr.remove("toxic")
            from core.event_manager import event_manager
            event_manager.emit("item_used", {
                "item_id": self.item_id,
                "effect": "cure_poison",
            })
            return True

        elif self.effect == ConsumableEffect.CUSTOM:
            if self.use_callback is not None:
                return self.use_callback(player)
            return False

        return False

    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 消耗品"]
        if self.effect == ConsumableEffect.HEAL:
            lines.append(f"回复 HP: +{self.effect_value}")
        elif self.effect == ConsumableEffect.RESTORE_MP:
            lines.append(f"回复 Mana: +{self.effect_value}")
        elif self.effect == ConsumableEffect.CURE_POISON:
            lines.append("效果: 解毒")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines
