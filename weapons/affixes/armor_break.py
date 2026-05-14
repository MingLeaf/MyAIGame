# =============================================================
# weapons/affixes/armor_break.py —— 破甲词条（无视 15% 防御）
#
# 功能：
#   将 AttackData.armor_pierce 写入指定百分比（默认 0.15）。
#   伤害计算时（damage_calculator）应在防御减免前先扣除 defense × armor_pierce
#   ——本阶段先把字段灌进 AttackData，等待第 16 阶段统一在伤害管线里实装。
#
# 适合：
#   战斧 / 大剑 等针对重甲敌人的武器
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.affixes import WeaponAffix

if TYPE_CHECKING:
    from weapons.base_weapon import AttackData


class ArmorBreakAffix(WeaponAffix):
    """
    破甲词条。
    构造参数：
        ratio : 无视防御百分比（默认 0.15 → 无视 15% 防御）
    """

    affix_id     = "armor_break"
    display_name = "破甲"
    rarity       = "rare"

    def __init__(self, ratio: float = 0.15):
        self.ratio: float = max(0.0, min(ratio, 1.0))

    def modify_attack(self, data: "AttackData", is_heavy: bool = False) -> "AttackData":
        # 重攻击破甲效果加成（×1.5）
        eff = self.ratio * (1.5 if is_heavy else 1.0)
        data.armor_pierce = max(data.armor_pierce, min(1.0, eff))
        # 同时附带额外韧性伤害（破甲也削韧性）
        data.poise_damage = data.poise_damage + (4.0 if is_heavy else 2.0)
        return data

    def get_description(self) -> str:
        return f"破甲：无视目标 {self.ratio*100:.0f}% 防御，韧性伤害提升"
