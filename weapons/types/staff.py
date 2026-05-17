# =============================================================
# weapons/types/staff.py —— 法杖
#
# 定位：
#   远程魔法武器。轻攻击 = 近战拍击（兜底自卫），
#   重攻击 = 蓄力魔法弹（自动生成 MagicBall）。
#
# 战技：魔法弹幕（Arcane Barrage）
#   - 消耗 30 灵力
#   - 一次发射 5 颗 MagicBall（扇形展开）
#   - 元素继承武器自身（默认 arcane → 受强化路线影响时变 fire/ice/lightning）
# =============================================================
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.weapon_art  import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


def _spawn_magic_ball(player: "Player", area, *,
                      damage: int = 18,
                      element: str = "arcane",
                      vx: float = 600.0,
                      vy: float = 0.0,
                      poise_damage: float = 8.0,
                      lifetime: float = 2.5):
    """生成一颗 MagicBall 并加入 area.projectiles。返回 ball 或 None。"""
    from physics.projectile import MagicBall
    ball = MagicBall(
        x = player.rect.centerx + (player.facing or 1) * 18,
        y = player.rect.centery - 4,
        vx = vx,
        vy = vy,
        damage = damage,
        owner = player,
        element = element,
        poise_damage = poise_damage,
        lifetime = lifetime,
    )
    if area is not None and hasattr(area, "projectiles"):
        area.projectiles.append(ball)
        return ball
    return None


class StaffArcaneBarrageArt(WeaponArt):
    """法杖战技：魔法弹幕（5 颗扇形 MagicBall）。"""

    art_id        = "staff_arcane_barrage"
    display_name  = "魔法弹幕"
    mana_cost     = 30
    cooldown      = 2.4
    poise_damage  = 12.0
    description   = "向前发射 5 颗追击魔法弹"

    def _execute(self, player: "Player", area) -> None:
        weapon = player.weapon
        wd = weapon.get_heavy_attack()
        facing = player.facing or 1

        # 5 颗扇形：-20° / -10° / 0° / +10° / +20°
        angles = (-20, -10, 0, 10, 20)
        speed  = 540.0
        per_dmg = max(8, int(wd.damage * 0.7))
        for deg in angles:
            rad = math.radians(deg)
            vx  = math.cos(rad) * speed * facing
            vy  = math.sin(rad) * speed
            _spawn_magic_ball(
                player, area,
                damage=per_dmg,
                element=wd.element,
                vx=vx, vy=vy,
                poise_damage=self.poise_damage / 5.0,
                lifetime=2.0,
            )


class Staff(BaseWeapon):
    """
    奥术法杖。

    轻攻击：6 / 7 / 9（近战兜底，伤害低）
    重攻击：18（前方释放一颗 MagicBall）
    元素：arcane（不受 holy / 物理克制表影响，由强化覆盖为 fire/ice/...）
    """

    weapon_type  = WeaponType.STAFF
    display_name = "奥术法杖"
    color        = (180, 140, 240)

    _base_light_dmg  = 6
    _base_heavy_dmg  = 18
    _element         = "arcane"

    _light_stamina   = 10.0
    _heavy_stamina   = 22.0   # 重攻击主要消耗灵力，但仍占点耐力

    _light_knockback = 100.0
    _heavy_knockback = 200.0

    _hb_offset_x   = 18
    _hb_offset_y   = 0
    _hb_w_light    = 32
    _hb_h_light    = 32
    _hb_w_heavy    = 40
    _hb_h_heavy    = 38
    _active_f_light = 5
    _active_f_heavy = 7

    _light_combo_mult = (1.0, 1.10, 1.30)
    _bleed_stack_light  = 0.0
    _poison_stack_light = 0.0

    _weapon_art_mana_cost = 30

    # 重攻击除了耗耐力，还要消耗灵力
    HEAVY_MANA_COST: int = 8

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = StaffArcaneBarrageArt()

    # ----------------------------------------------------------------
    # 法杖特有：发射魔法弹（由 PlayerCombat / 攻击状态调用）
    # ----------------------------------------------------------------

    def cast_magic_ball(self, player: "Player", area):
        """
        重攻击对外接口：扣灵力 + 发射一颗 MagicBall。
        若灵力不足或 area 无效返回 None。
        """
        stats = getattr(player, "stats", None)
        if stats is not None and not stats.consume_mana(self.HEAVY_MANA_COST):
            return None
        wd = self.get_heavy_attack()
        ball = _spawn_magic_ball(
            player, area,
            damage=wd.damage,
            element=wd.element,
            vx=560.0 * (player.facing or 1),
            vy=0.0,
            poise_damage=wd.poise_damage,
            lifetime=2.5,
        )
        # 若 area 无效导致魔法弹未加入 projectiles，返还灵力
        if ball is None and stats is not None:
            stats.mana = min(stats.max_mana, stats.mana + self.HEAVY_MANA_COST)
        return ball
