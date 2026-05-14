# =============================================================
# weapons/sword.py —— 单手剑（骑士剑）
#
# 定位：均衡速度与伤害，三段连击流畅，兼容盾牌
# 元素：physical（物理）
# 特色：无特殊状态积累
# =============================================================
from __future__ import annotations
from weapons.base_weapon import BaseWeapon, WeaponType
from weapons.sword_art  import SwordCycloneArt


class Sword(BaseWeapon):
    """
    骑士剑 —— 初始武器，均衡型。

    轻攻击：10 / 11 / 13（三段连击倍率递增）
    重攻击：22
    元素：physical
    """

    weapon_type  = WeaponType.SWORD
    display_name = "骑士剑"
    color        = (180, 180, 220)

    _base_light_dmg  = 10
    _base_heavy_dmg  = 22
    _element         = "physical"

    _light_stamina   = 12.0
    _heavy_stamina   = 28.0

    _light_knockback = 160.0
    _heavy_knockback = 260.0

    _hb_offset_x   = 22
    _hb_offset_y   = 0
    _hb_w_light    = 42
    _hb_h_light    = 36
    _hb_w_heavy    = 50
    _hb_h_heavy    = 40
    _active_f_light = 6
    _active_f_heavy = 8

    _light_combo_mult = (1.0, 1.1, 1.3)

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = SwordCycloneArt()
