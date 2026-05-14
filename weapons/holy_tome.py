# =============================================================
# weapons/holy_tome.py —— 圣典（神圣典籍）
#
# 定位：神圣属性伤害，对不死族强效，同时支持治疗
# 元素：holy（对不死族 ×1.5，对人类普通）
# 特色：重攻击为神圣爆发，轻攻击为近战打击
# =============================================================
from __future__ import annotations
from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.holy_tome_art import HolyTomeLightArt


class HolyTome(BaseWeapon):
    """
    神圣典籍。

    轻攻击：12（近战+神圣，对不死 ×1.5）
    重攻击：28（神圣爆发，范围略大）
    元素：holy
    """

    weapon_type  = WeaponType.HOLY_TOME
    display_name = "神圣典籍"
    color        = (255, 240, 120)

    _base_light_dmg  = 12
    _base_heavy_dmg  = 28
    _element         = "holy"      # 神圣元素：克制不死

    _light_stamina   = 14.0
    _heavy_stamina   = 32.0

    _light_knockback = 160.0
    _heavy_knockback = 300.0

    _hb_offset_x   = 20
    _hb_offset_y   = 0
    _hb_w_light    = 44
    _hb_h_light    = 38
    _hb_w_heavy    = 56
    _hb_h_heavy    = 50
    _active_f_light = 6
    _active_f_heavy = 9

    _light_combo_mult   = (1.0, 1.1, 1.2)
    _bleed_stack_light  = 0.0
    _poison_stack_light = 0.0

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = HolyTomeLightArt()
