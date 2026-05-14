# =============================================================
# weapons/greatsword_art.py —— 大剑战技：天崩地裂
#
# game_rule.md §6.3：
#   跳起重劈，巨大范围震地，强力击晕
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.weapon_art import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


class GreatswordQuakeArt(WeaponArt):
    """大剑战技：天崩地裂。"""

    art_id        = "greatsword_quake"
    display_name  = "天崩地裂"
    mana_cost     = 28
    cooldown      = 2.5
    poise_damage  = 50.0
    description   = "跳起重劈，巨大范围震地，强力击晕"

    def _execute(self, player: "Player", area) -> None:
        from entities.player.attack_hitbox import AttackHitbox
        weapon = player.weapon
        wd = weapon.get_heavy_attack()

        # 极大型判定框（全屏震地），高击退力 + 强眩晕
        hb = AttackHitbox(
            owner_rect    = player.rect,
            facing        = player.facing,
            offset_x      = -60,
            offset_y      = -30,
            width         = 180,
            height        = 100,
            damage        = int(wd.damage * 1.8),
            active_frames = max(wd.active_frames, 10),
            knockback     = wd.knockback * 2.0,
            element       = wd.element,
            poise_damage  = self.poise_damage,
            source        = player,
        )
        player.active_hitboxes.append(hb)
