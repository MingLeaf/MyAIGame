# =============================================================
# weapons/dagger_art.py —— 匕首战技：幻影步
#
# game_rule.md §6.3：
#   瞬间闪至敌人身后，背刺爆伤
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.weapon_art import WeaponArt

if TYPE_CHECKING:
    from entities.player.player import Player


class DaggerPhantomStepArt(WeaponArt):
    """匕首战技：幻影步。"""

    art_id        = "dagger_phantom_step"
    display_name  = "幻影步"
    mana_cost     = 15
    cooldown      = 1.2
    poise_damage  = 10.0
    description   = "瞬间闪至敌人身后，背刺爆伤"

    def _execute(self, player: "Player", area) -> None:
        from entities.player.attack_hitbox import AttackHitbox
        weapon = player.weapon

        # 找到最近的敌人，闪至其身后
        if area is not None:
            enemies = getattr(area, "enemies", [])
            nearest = None
            nearest_dist = 180  # 最大闪现距离

            for e in enemies:
                if getattr(e, "dead", False):
                    continue
                dx = e.rect.centerx - player.rect.centerx
                dy = e.rect.centery - player.rect.centery
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = e

            if nearest is not None:
                # 闪现到敌人身后
                behind_x = nearest.rect.centerx
                if player.rect.centerx < nearest.rect.centerx:
                    behind_x = nearest.rect.left - 40  # 敌人左侧（面对玩家的身后）
                else:
                    behind_x = nearest.rect.right + 40
                player.rect.centerx = int(behind_x)
                player.rect.centery = nearest.rect.centery
                player.x = player.rect.centerx
                player.y = player.rect.centery
                player.facing = 1 if player.rect.centerx < nearest.rect.centerx else -1

        # 生成高伤害背刺判定
        wd = weapon.get_heavy_attack()
        hb = AttackHitbox(
            owner_rect    = player.rect,
            facing        = player.facing,
            offset_x      = wd.hb_offset_x,
            offset_y      = wd.hb_offset_y,
            width         = wd.hb_width,
            height        = wd.hb_height,
            damage        = int(wd.damage * 2.0),  # 背刺 2 倍伤害
            active_frames = wd.active_frames,
            knockback     = wd.knockback,
            element       = wd.element,
            poise_damage  = self.poise_damage,
            source        = player,
        )
        player.active_hitboxes.append(hb)
