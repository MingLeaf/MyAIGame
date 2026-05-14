# =============================================================
# weapons/greatsword.py —— 大剑（巨剑/圣战重剑）
#
# 定位：高伤害大范围，速度慢，双手持用，强力破格
# 元素：physical
# 特色：重攻击范围极大，击退力强，高韧性伤害
# =============================================================
from __future__ import annotations
from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.greatsword_art import GreatswordQuakeArt


class Greatsword(BaseWeapon):
    """
    圣战重剑。

    轻攻击：18 / 20 / 25（连段慢但每段伤害高）
    重攻击：40（范围巨大，强力震地）
    元素：physical
    """

    weapon_type  = WeaponType.GREATSWORD
    display_name = "圣战重剑"
    color        = (220, 200, 80)

    _base_light_dmg  = 18
    _base_heavy_dmg  = 40
    _element         = "physical"

    _light_stamina   = 22.0
    _heavy_stamina   = 45.0

    _light_knockback = 240.0
    _heavy_knockback = 400.0

    # 判定框更大（大剑攻击范围宽）
    _hb_offset_x   = 28
    _hb_offset_y   = 0
    _hb_w_light    = 56
    _hb_h_light    = 44
    _hb_w_heavy    = 72
    _hb_h_heavy    = 56
    _active_f_light = 7
    _active_f_heavy = 10

    _light_combo_mult = (1.0, 1.1, 1.4)

    # 无状态积累，但韧性伤害极高（在 AttackData 中 poise_damage 会更高）
    _bleed_stack_light  = 0.0
    _poison_stack_light = 0.0

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = GreatswordQuakeArt()

    def get_light_attack(self, combo_step: int = 0) -> AttackData:
        """大剑轻攻击：韧性伤害更高，步兵需2~3次破韧。"""
        data = super().get_light_attack(combo_step)
        # 大剑比基类多给一倍韧性伤害（叠加强化的韧性倍率）
        data.poise_damage = (8.0 + combo_step * 2.0) * self._upgrade_poise_mult
        return data

    def get_heavy_attack(self):
        """大剑重攻击：超高韧性伤害，对步兵/不死族直接破韧，重甲兵需2次。"""
        data = super().get_heavy_attack()
        # 步兵20直接破；不死族60需2次；重甲100需3次（叠加强化倍率）
        data.poise_damage = 35.0 * self._upgrade_poise_mult
        return data
