# =============================================================
# weapons/sword_art.py —— 单手剑战技：旋风斩
#
# game_rule.md §6.3：
#   360度旋转斩击，打飞周围敌人
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.weapon_art import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


class SwordCycloneArt(WeaponArt):
    """单手剑战技：旋风斩。"""

    art_id        = "sword_cyclone"
    display_name  = "旋风斩"
    mana_cost     = 20
    cooldown      = 1.6
    poise_damage  = 25.0
    description   = "360度旋转斩击，打飞周围敌人"

    def _execute(self, player: "Player", area) -> None:
        from entities.player.attack_hitbox import AttackHitbox
        weapon = player.weapon
        wd = weapon.get_heavy_attack()

        # 超大范围判定框（覆盖周身）
        hb = AttackHitbox(
            owner_rect    = player.rect,
            facing        = player.facing,
            offset_x      = -30,
            offset_y      = -20,
            width         = 120,
            height        = 80,
            damage        = int(wd.damage * 1.3),
            active_frames = max(wd.active_frames, 6),
            knockback     = wd.knockback * 1.5,
            element       = wd.element,
            poise_damage  = self.poise_damage,
            source        = player,
        )
        player.active_hitboxes.append(hb)
