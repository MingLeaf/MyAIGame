# =============================================================
# weapons/types/spear.py —— 长矛
#
# 定位：
#   长距离突刺，攻击范围最远（hb_offset_x 大），
#   速度中等，重攻击为大力突刺。
#
# 战技：盾突反击（Counter Thrust）
#   - 消耗 18 灵力
#   - 在玩家身前生成一次大范围突刺判定（穿透多个敌人）
#   - 命中后将敌人击退，并对处于"前摇/吟唱"状态的敌人造成 ×1.5 伤害
#     （由判定框带 is_counter 标记，受击端读取）
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.weapon_art  import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


class SpearCounterArt(WeaponArt):
    """长矛战技：盾突反击。"""

    art_id        = "spear_counter"
    display_name  = "盾突反击"
    mana_cost     = 18
    cooldown      = 1.4
    poise_damage  = 22.0
    description   = "向前突刺，对吟唱中的敌人造成 1.5 倍伤害"

    def _execute(self, player: "Player", area) -> None:
        from entities.player.attack_hitbox import AttackHitbox
        weapon = player.weapon
        wd = weapon.get_heavy_attack()
        # 生成超大范围判定框（突刺）
        hb = AttackHitbox(
            owner_rect    = player.rect,
            facing        = player.facing,
            offset_x      = max(wd.hb_offset_x + 40, 60),
            offset_y      = wd.hb_offset_y,
            width         = max(wd.hb_width + 60, 100),
            height        = wd.hb_height,
            damage        = int(wd.damage * 1.4),
            active_frames = max(wd.active_frames, 8),
            knockback     = wd.knockback * 1.2,
            element       = wd.element,
            poise_damage  = self.poise_damage,
            source        = player,
        )
        # 反击标记（敌人若在前摇/吟唱由其受击逻辑读取）
        try:
            hb.is_counter = True   # type: ignore[attr-defined]
        except Exception:
            pass
        player.active_hitboxes.append(hb)


class Spear(BaseWeapon):
    """
    长矛 —— 远距离突刺武器。

    轻攻击：12 / 13 / 16
    重攻击：26（大力突刺，韧性破甲较好）
    元素：physical
    """

    weapon_type  = WeaponType.SPEAR
    display_name = "战长矛"
    color        = (200, 180, 160)

    _base_light_dmg  = 12
    _base_heavy_dmg  = 26
    _element         = "physical"

    _light_stamina   = 14.0
    _heavy_stamina   = 30.0

    _light_knockback = 180.0
    _heavy_knockback = 320.0

    # 长矛攻击范围远（offset_x 大）
    _hb_offset_x   = 38
    _hb_offset_y   = 0
    _hb_w_light    = 60
    _hb_h_light    = 28
    _hb_w_heavy    = 80
    _hb_h_heavy    = 32
    _active_f_light = 5
    _active_f_heavy = 7

    _light_combo_mult = (1.0, 1.10, 1.30)

    _bleed_stack_light  = 15.0     # 轻微流血
    _poison_stack_light = 0.0

    _weapon_art_mana_cost = 18

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = SpearCounterArt()

    def get_light_attack(self, combo_step: int = 0) -> AttackData:
        """长矛轻攻击：基础 + 第三段稍大判定（"全力突刺"）。"""
        data = super().get_light_attack(combo_step)
        if combo_step >= 2:
            data.hb_width  = int(data.hb_width * 1.15)
            data.poise_damage += 2.0 * self._upgrade_poise_mult
        return data
