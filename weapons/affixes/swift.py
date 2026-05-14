# =============================================================
# weapons/affixes/swift.py —— 攻速 +10% 词条
#
# 功能：
#   - active_frames *= 0.9（攻击判定时间 -10%，间接提升出招速度）
#   - stamina_cost  *= 0.9（耐力消耗 -10%，可连段更多次）
#
# 适合：
#   匕首 / 单手剑 等高速武器，强化"打手"流派
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.affixes import WeaponAffix

if TYPE_CHECKING:
    from weapons.base_weapon import AttackData


class SwiftAffix(WeaponAffix):
    """
    迅捷词条。
    构造参数：
        ratio : 攻速提升幅度（默认 0.10 → +10%）
    """

    affix_id     = "swift"
    display_name = "迅捷"
    rarity       = "common"

    def __init__(self, ratio: float = 0.10):
        # ratio = 0.10 → 出手时间 / 耐力 ×0.9
        self.ratio: float = max(0.0, min(ratio, 0.5))

    def modify_attack(self, data: "AttackData", is_heavy: bool = False) -> "AttackData":
        speed_mult = 1.0 - self.ratio
        # active_frames 至少保留 1 帧
        data.active_frames = max(1, int(round(data.active_frames * speed_mult)))
        data.stamina_cost  = data.stamina_cost * speed_mult
        return data

    def get_description(self) -> str:
        return f"迅捷：攻击速度 +{self.ratio*100:.0f}%，耐力消耗 -{self.ratio*100:.0f}%"
