# =============================================================
# weapons/types/axe.py —— 战斧
#
# 定位：
#   高伤害 + 破盾特性。轻攻击数值偏高、连段速度慢，
#   对持盾敌人附加破盾增益（破盾后受击 ×1.5）。
#
# 战技：碎盾劈砍（Shield Crush）
#   - 消耗 22 灵力
#   - 在玩家身前生成"破盾"判定框（armor_pierce=0.5、特殊韧性伤害）
#   - 命中持盾敌人时，将其 BlockComponent.is_blocking 设为 False（如有）
#     并附加一次 60 韧性伤害
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.weapon_art  import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


class AxeShieldCrushArt(WeaponArt):
    """战斧战技：碎盾劈砍。"""

    art_id        = "axe_shield_crush"
    display_name  = "碎盾劈砍"
    mana_cost     = 22
    cooldown      = 2.0
    poise_damage  = 60.0
    description   = "强力下劈，破除目标格挡并造成大量韧性伤害"

    def _execute(self, player: "Player", area) -> None:
        from entities.player.attack_hitbox import AttackHitbox
        weapon = player.weapon
        wd = weapon.get_heavy_attack()
        hb = AttackHitbox(
            owner_rect    = player.rect,
            facing        = player.facing,
            offset_x      = wd.hb_offset_x,
            offset_y      = wd.hb_offset_y - 4,
            width         = max(wd.hb_width + 30, 80),
            height        = max(wd.hb_height + 20, 60),
            damage        = int(wd.damage * 1.6),
            active_frames = max(wd.active_frames, 10),
            knockback     = wd.knockback * 1.4,
            element       = wd.element,
            poise_damage  = self.poise_damage,
            source        = player,
        )
        # 破盾标记
        try:
            hb.shield_break = True       # type: ignore[attr-defined]
            hb.armor_pierce = 0.5        # type: ignore[attr-defined]
        except Exception:
            pass
        player.active_hitboxes.append(hb)


class Axe(BaseWeapon):
    """
    双手战斧 —— 高伤破盾武器。

    轻攻击：15 / 17 / 21
    重攻击：35（强力下劈，破甲性能优秀）
    元素：physical
    """

    weapon_type  = WeaponType.AXE
    display_name = "破阵战斧"
    color        = (200, 130, 80)

    _base_light_dmg  = 15
    _base_heavy_dmg  = 35
    _element         = "physical"

    _light_stamina   = 18.0
    _heavy_stamina   = 38.0

    _light_knockback = 220.0
    _heavy_knockback = 380.0

    _hb_offset_x   = 26
    _hb_offset_y   = -2
    _hb_w_light    = 50
    _hb_h_light    = 42
    _hb_w_heavy    = 64
    _hb_h_heavy    = 54
    _active_f_light = 6
    _active_f_heavy = 9

    _light_combo_mult = (1.0, 1.10, 1.30)
    _bleed_stack_light  = 20.0     # 战斧轻流血
    _poison_stack_light = 0.0

    _weapon_art_mana_cost = 22

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = AxeShieldCrushArt()

    def get_light_attack(self, combo_step: int = 0) -> AttackData:
        """战斧轻攻击：自带 5% 破甲；韧性伤害高一档。"""
        data = super().get_light_attack(combo_step)
        # 5% 基础破甲（与词条/战技叠加）
        data.armor_pierce = max(data.armor_pierce, 0.05)
        # 韧性伤害 +2（叠加强化倍率）
        data.poise_damage += 2.0 * self._upgrade_poise_mult
        return data

    def get_heavy_attack(self) -> AttackData:
        """战斧重攻击：自带 10% 破甲。"""
        data = super().get_heavy_attack()
        data.armor_pierce = max(data.armor_pierce, 0.10)
        data.poise_damage = data.poise_damage + 6.0 * self._upgrade_poise_mult
        return data
