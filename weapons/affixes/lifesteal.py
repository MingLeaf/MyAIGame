# =============================================================
# weapons/affixes/lifesteal.py —— 吸血词条
#
# 功能：
#   挂载后将 AttackData.lifesteal 设为指定百分比（默认 8%）。
#   实际治疗逻辑：
#     1. AttackData 字段被注入到 AttackHitbox（通过 hitbox 属性透传）
#     2. 武器击中目标后，由 hit_resolver 或本词条订阅的 "weapon_hit" 事件
#        计算 actual_dmg × lifesteal 并调用 player.stats.heal()
#
# 当前阶段（第 5 阶段）：
#   先把 lifesteal 字段写到 AttackData 上，让伤害管线/事件订阅者拾取。
#   订阅 event_manager.on("weapon_hit", ...) 用于即时回血（如果数据可用）。
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.affixes import WeaponAffix
from core.event_manager import event_manager

if TYPE_CHECKING:
    from weapons.base_weapon import BaseWeapon, AttackData


class LifestealAffix(WeaponAffix):
    """
    吸血词条。
    构造参数：
        ratio : 吸血比例（默认 0.08，即 8%；推荐范围 0.05~0.10）
    """

    affix_id     = "lifesteal"
    display_name = "吸血"
    rarity       = "rare"

    def __init__(self, ratio: float = 0.08):
        self.ratio: float = max(0.0, min(ratio, 1.0))
        self._owner_weapon: "BaseWeapon" = None  # type: ignore

    # ---- 生命周期 ----

    def on_attach(self, weapon: "BaseWeapon") -> None:
        self._owner_weapon = weapon
        # 订阅命中事件（事件载荷需含 attacker_weapon, damage_dealt, attacker）
        event_manager.subscribe("weapon_hit", self._on_weapon_hit)

    def on_detach(self, weapon: "BaseWeapon") -> None:
        event_manager.unsubscribe("weapon_hit", self._on_weapon_hit)
        self._owner_weapon = None  # type: ignore

    # ---- 修饰 AttackData ----

    def modify_attack(self, data: "AttackData", is_heavy: bool = False) -> "AttackData":
        # 重攻击 ×1.25 吸血
        data.lifesteal = max(data.lifesteal, self.ratio * (1.25 if is_heavy else 1.0))
        return data

    # ---- 事件回调 ----

    def _on_weapon_hit(self, payload: dict) -> None:
        """
        weapon_hit 事件载荷规范（约定）：
            {
              "weapon":        BaseWeapon,        # 出招武器
              "attacker":      object,            # 攻击者（带 .stats.heal）
              "damage_dealt":  int,
              "is_heavy":      bool,
            }
        若载荷不完整，忽略。
        """
        if self._owner_weapon is None:
            return
        if payload.get("weapon") is not self._owner_weapon:
            return
        attacker = payload.get("attacker")
        dmg      = int(payload.get("damage_dealt", 0))
        if attacker is None or dmg <= 0:
            return
        stats = getattr(attacker, "stats", None)
        if stats is None or not hasattr(stats, "heal"):
            return
        is_heavy = bool(payload.get("is_heavy", False))
        ratio    = self.ratio * (1.25 if is_heavy else 1.0)
        heal_amt = max(1, int(dmg * ratio))
        stats.heal(heal_amt)

    def get_description(self) -> str:
        return f"吸血：每次命中将 {self.ratio*100:.0f}% 伤害转化为生命"
