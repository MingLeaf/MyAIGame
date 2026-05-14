# =============================================================
# weapons/affixes/status_boost.py —— 状态积累 +20% 词条
#
# 功能：
#   bleed/poison/burn/freeze/shock 全部状态积累量 ×1.20
#
# 适合：
#   匕首（流血流）/ 法杖（元素状态流）
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.affixes import WeaponAffix

if TYPE_CHECKING:
    from weapons.base_weapon import AttackData


# 受影响的所有状态字段名
_STATUS_FIELDS = (
    "bleed_stack", "poison_stack",
    "burn_stack",  "freeze_stack", "shock_stack",
)


class StatusBoostAffix(WeaponAffix):
    """
    状态积累 +20% 词条。
    构造参数：
        ratio : 提升倍率（默认 0.20 → ×1.20）
    """

    affix_id     = "status_boost"
    display_name = "毒研"   # 偏 dagger 风
    rarity       = "rare"

    def __init__(self, ratio: float = 0.20):
        self.ratio: float = max(0.0, ratio)

    def modify_attack(self, data: "AttackData", is_heavy: bool = False) -> "AttackData":
        mult = 1.0 + self.ratio
        for field_name in _STATUS_FIELDS:
            cur = getattr(data, field_name, 0.0)
            if cur > 0.0:
                setattr(data, field_name, cur * mult)
        return data

    def get_description(self) -> str:
        return f"状态强化：所有状态积累 +{self.ratio*100:.0f}%"
