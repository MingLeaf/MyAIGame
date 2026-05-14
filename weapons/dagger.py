# =============================================================
# weapons/dagger.py —— 匕首（毒刃/暗影刀）
#
# 定位：极速连击，单段伤害低但连段快，高暴击，易触发流血/毒
# 元素：physical（但可附带 poison 积累）
# 特色：每次命中积累流血/中毒值（较高），适合背刺触发
# =============================================================
from __future__ import annotations
from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.dagger_art import DaggerPhantomStepArt


class Dagger(BaseWeapon):
    """
    暗影匕首。

    轻攻击：7 / 8 / 9（连段速度最快，判定帧最短）
    重攻击：18（高速刺击，附带流血）
    元素：physical
    流血积累：每次命中 +40（轻）/ +80（重）
    """

    weapon_type  = WeaponType.DAGGER
    display_name = "暗影匕首"
    color        = (180, 60, 80)

    _base_light_dmg  = 7
    _base_heavy_dmg  = 18
    _element         = "physical"

    _light_stamina   = 8.0    # 耐力消耗极低
    _heavy_stamina   = 20.0

    _light_knockback = 100.0  # 击退弱
    _heavy_knockback = 180.0

    # 判定框更小（近身武器）
    _hb_offset_x   = 16
    _hb_offset_y   = 4
    _hb_w_light    = 30
    _hb_h_light    = 28
    _hb_w_heavy    = 36
    _hb_h_heavy    = 32
    _active_f_light = 4   # 判定帧短，但连段间隔也短
    _active_f_heavy = 5

    _light_combo_mult = (1.0, 1.05, 1.15)

    # 流血积累：匕首高流血，每次轻攻击命中积累 40
    _bleed_stack_light  = 40.0
    _poison_stack_light = 15.0   # 轻微毒积累

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = DaggerPhantomStepArt()
