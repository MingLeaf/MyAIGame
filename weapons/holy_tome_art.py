# =============================================================
# weapons/holy_tome_art.py —— 圣典战技：神圣之光
#
# game_rule.md §6.3：
#   治疗+神圣伤害（圣典本身兼具治疗和神圣伤害特性）
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.weapon_art import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


class HolyTomeLightArt(WeaponArt):
    """圣典战技：神圣之光。"""

    art_id        = "holy_tome_light"
    display_name  = "神圣之光"
    mana_cost     = 25
    cooldown      = 2.0
    poise_damage  = 30.0
    description   = "释放神圣冲击波，对不死族造成 2 倍伤害并恢复自身 HP"

    def _execute(self, player: "Player", area) -> None:
        from entities.player.attack_hitbox import AttackHitbox
        weapon = player.weapon
        wd = weapon.get_heavy_attack()

        # 前方扇形范围判定
        hb = AttackHitbox(
            owner_rect    = player.rect,
            facing        = player.facing,
            offset_x      = wd.hb_offset_x,
            offset_y      = -20,
            width         = wd.hb_width + 40,
            height        = 80,
            damage        = int(wd.damage * 1.5),
            active_frames = max(wd.active_frames, 8),
            knockback     = wd.knockback * 0.5,
            element       = "holy",
            poise_damage  = self.poise_damage,
            source        = player,
        )
        # 标记为神圣属性（对抗不死族时由伤害计算器读取）
        player.active_hitboxes.append(hb)

        # 自我治疗：恢复 25% 最大 HP
        heal_amount = int(player.stats.max_hp * 0.25)
        player.stats.heal(heal_amount)
