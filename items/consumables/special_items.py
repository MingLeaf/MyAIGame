# =============================================================
# items/consumables/special_items.py —— 特殊消耗品
#
# 包含：诅咒解符 / 骷髅骨灰 / 传送石 / 陷阱炸弹 / 毒飞镖
#
# 各类效果通过 special_kind 分发：
#   - curse_remover  : 解除诅咒状态
#   - skeleton_ashes : 召唤骷髅友军（事件，由 NPC/AI 系统接管）
#   - teleport_stone : 传送回最近营地（事件，由 campfire_system 接管）
#   - trap_bomb      : 在脚下放置炸弹陷阱
#   - poison_dart    : 投掷有毒飞镖（生成 Arrow 抛射物）
#
# 设计：本模块只负责"行为入口"，具体效果对应的子系统在后续阶段
#       通过订阅事件接管。
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Any

from items.consumable import ConsumableItem, ConsumableEffect
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class SpecialItem(ConsumableItem):
    """特殊消耗品（解符/骨灰/传送石/陷阱/飞镖）。"""

    special_kind: str = "generic"
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.effect = ConsumableEffect.CUSTOM

    # ----------------------------------------------------------------
    # 入口
    # ----------------------------------------------------------------

    def use(self, player: "Player") -> bool:
        kind = self.special_kind
        ok = False

        if kind == "curse_remover":
            ok = self._do_curse_remover(player)
        elif kind == "skeleton_ashes":
            ok = self._do_summon_ally(player, "skeleton")
        elif kind == "teleport_stone":
            ok = self._do_teleport(player)
        elif kind == "trap_bomb":
            ok = self._do_place_trap(player, "bomb")
        elif kind == "poison_dart":
            ok = self._do_throw_poison_dart(player)
        else:
            return False

        if ok:
            event_manager.emit("item_used", {
                "item_id": self.item_id,
                "effect":  "special",
                "kind":    kind,
            })
        return ok

    # ----------------------------------------------------------------
    # 各类效果
    # ----------------------------------------------------------------

    def _do_curse_remover(self, player: "Player") -> bool:
        status = getattr(player, "status", None)
        if status is not None:
            status.remove("curse")
        event_manager.emit("curse_removed", {"player": player})
        return True

    def _do_summon_ally(self, player: "Player", ally_id: str) -> bool:
        event_manager.emit("summon_ally", {
            "ally_id": ally_id,
            "player":  player,
            "x":       player.rect.centerx if hasattr(player, "rect") else 0,
            "y":       player.rect.bottom  if hasattr(player, "rect") else 0,
        })
        return True

    def _do_teleport(self, player: "Player") -> bool:
        event_manager.emit("teleport_to_campfire", {
            "player": player,
            "campfire_id": self.extra.get("campfire_id"),  # None = 最近
        })
        return True

    def _do_place_trap(self, player: "Player", trap_type: str) -> bool:
        if not hasattr(player, "rect"):
            return False
        damage = int(self.extra.get("damage", 50))
        event_manager.emit("place_trap", {
            "player":    player,
            "trap_type": trap_type,
            "x":         player.rect.centerx,
            "y":         player.rect.bottom,
            "damage":    damage,
        })
        return True

    def _do_throw_poison_dart(self, player: "Player") -> bool:
        area = getattr(player, "current_area", None)
        if area is None or not hasattr(area, "projectiles"):
            # 区域不可用时只发事件
            event_manager.emit("special_item_failed", {
                "item_id": self.item_id, "reason": "no_area"
            })
            return False
        from physics.projectile import Arrow
        facing = getattr(player, "facing", 1) or 1
        damage = int(self.extra.get("damage", 8))
        poison_stack = float(self.extra.get("poison_stack", 30.0))
        dart = Arrow(
            x = player.rect.centerx + facing * 12,
            y = player.rect.centery,
            vx = 600.0 * facing,
            vy = -50.0,
            damage = damage,
            owner = player,
            element = "poison",
            poise_damage = 4.0,
            lifetime = 2.0,
        )
        # 标记附加毒积累（HitResolver 命中时可读此字段）
        try:
            dart.poison_stack = poison_stack   # type: ignore[attr-defined]
        except Exception:
            pass
        area.projectiles.append(dart)
        return True

    # ----------------------------------------------------------------
    def get_tooltip_lines(self) -> list[str]:
        lines = [self.name, "类型: 特殊道具"]
        lines.append(f"效果类型: {self.special_kind}")
        lines.append(f"重量: {self.weight:.1f} kg")
        if self.description:
            lines.append(self.description)
        return lines


__all__ = ["SpecialItem"]
