# =============================================================
# combat/hit_resolver.py —— 判定框碰撞检测（每帧扫描）
#
# HitResolver.update(player, enemy_list, ftm) 每帧调用：
#   - 遍历 player.active_hitboxes
#   - 检测与各敌人 rect 的碰撞
#   - 命中后：调用 DamageCalculator 计算最终伤害
#             调用 enemy.take_damage()
#             向 FloatingTextManager 推送飘字
#             发布 HIT_EVENT 音效事件
# =============================================================
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING, Optional

from combat.damage_calculator import (
    DamageCalculator, HitInfo, AttackerStats, DefenderStats,
)
from combat.floating_text  import FloatingTextManager
from combat.status_effect  import BleedEffect

if TYPE_CHECKING:
    from entities.player.player import Player
    from entities.enemy.base_enemy import BaseEnemy


# ---- 自定义事件类型（音效系统通过 event 总线接收） ----
HIT_EVENT_TYPE = pygame.USEREVENT + 10

# 每次命中叠加的流血积累值（满 100 爆发扣 15% 当前HP）
_BLEED_STACK_PER_HIT = 30.0


def _post_hit_sound(sound_name: str = "hit_flesh") -> None:
    """发布打击音效事件到 pygame 事件队列。"""
    evt = pygame.event.Event(HIT_EVENT_TYPE, {"sound": sound_name})
    pygame.event.post(evt)


class HitResolver:
    """
    每帧扫描玩家攻击判定框与敌人的碰撞，计算并施加伤害。

    可选通过构造函数传入 FloatingTextManager；
    也可在游戏场景初始化完成后通过 bind_ftm() 注入。
    """

    def __init__(self, ftm: Optional[FloatingTextManager] = None):
        self._ftm: Optional[FloatingTextManager] = ftm
        self._calc = DamageCalculator()

    def bind_ftm(self, ftm: FloatingTextManager) -> None:
        self._ftm = ftm

    # ----------------------------------------------------------------
    # 主入口：每帧调用
    # ----------------------------------------------------------------

    def update(self, player: "Player", enemy_list: list["BaseEnemy"]) -> None:
        """
        扫描 player.active_hitboxes，逐一与 enemy_list 检测碰撞。
        命中则计算伤害、施加伤害、生成飘字、发布音效事件。
        """
        if not player or not getattr(player, "active_hitboxes", None):
            return

        for hb in player.active_hitboxes:
            if not hb.active:
                continue

            for enemy in enemy_list:
                if enemy.is_dead:
                    continue

                eid = id(enemy)
                if not hb.can_hit(eid):
                    continue

                if not hb.rect.colliderect(enemy.rect):
                    continue

                # ---------- 命中处理 ----------
                hb.register_hit(eid)
                self._resolve_hit(player, hb, enemy)

    # ----------------------------------------------------------------
    # 单次命中处理
    # ----------------------------------------------------------------

    def _resolve_hit(self, player, hb, enemy: "BaseEnemy") -> None:
        """计算伤害 → 施加 → 飘字 → 音效。"""

        # 1. 构建攻击方/防御方数值切片
        # player.stats.atk 已经包含：
        #   - growth.get_atk_bonus(weapon)（成长属性加成）
        #   - weapon_item_atk（WeaponItem.base_atk，由 Equipment._sync_stats 注入）
        p_stats = AttackerStats(
            atk=getattr(player.stats, "atk", hb.damage),
        )
        e_stats = DefenderStats(
            defense     = getattr(enemy.stats, "defense", 0),
            enemy_stats = getattr(enemy, "stats", None),   # 传入完整 EnemyStats 以查克制
        )

        # 2. 构建 HitInfo
        # 背刺：攻击方 facing 与敌人 facing 相同（偷背后）
        is_backstab = (
            hasattr(player, "facing") and hasattr(enemy, "facing") and
            player.facing == enemy.facing
        )

        # 冰冻增伤：查询敌人 status_manager
        freeze_bonus = 1.0
        if hasattr(enemy, "status") and hasattr(enemy.status, "frozen_damage_bonus"):
            freeze_bonus = enemy.status.frozen_damage_bonus()

        hit_info = HitInfo(
            base_damage      = hb.damage,
            skill_multiplier = 1.0,
            element          = getattr(hb, "element", "none"),
            is_backstab      = is_backstab,
            poise_damage     = getattr(hb, "poise_damage", 10.0),
        )

        # 3. 计算伤害
        final_dmg = self._calc.calculate(p_stats, e_stats, hit_info)

        # 应用冰冻增伤（在基础计算之外额外乘）
        if freeze_bonus > 1.0:
            final_dmg = max(1, int(final_dmg * freeze_bonus))

        # ---- 第 7 阶段补丁：套装攻击百分比加成 ----
        atk_pct = float(getattr(player.stats, "atk_bonus_pct", 0.0))
        if atk_pct != 0.0:
            final_dmg = max(1, int(final_dmg * (1.0 + atk_pct)))

        # 魔法元素再叠加 magic_bonus_pct（法师套装等）
        elem = hit_info.element
        if elem in ("fire", "ice", "lightning", "dark", "arcane", "holy", "magic"):
            magic_pct = float(getattr(player.stats, "magic_bonus_pct", 0.0))
            if magic_pct != 0.0:
                final_dmg = max(1, int(final_dmg * (1.0 + magic_pct)))

        # ---- 调试：一击必杀 ----
        import utils.debug as dbg
        if dbg.enabled and dbg.one_hit_kill:
            final_dmg = 99999  # 远超最大HP+防御，保证一击必杀
            hit_info = HitInfo(
                base_damage=final_dmg, skill_multiplier=1.0,
                element=hit_info.element, is_backstab=hit_info.is_backstab,
                poise_damage=9999.0,
            )

        # 4. 方向
        knockback_dir = 1 if enemy.x > player.x else -1

        # 5. 施加伤害（同时传入韧性伤害，轻/重攻击数值不同）
        enemy.take_damage(final_dmg, knockback_dir,
                          poise_damage=hit_info.poise_damage)

        # 6. 施加流血积累（从 hitbox 的 bleed_stack 读取，0 则跳过）
        bleed_stack = getattr(hb, "bleed_stack", _BLEED_STACK_PER_HIT)
        if bleed_stack > 0 and hasattr(enemy, "status"):
            if not enemy.status.has("bleed"):
                enemy.status.add(BleedEffect())
            bleed = enemy.status.get("bleed")
            if bleed is not None:
                bleed.add_stack(bleed_stack)

        # 7. 飘字
        if self._ftm is not None:
            wx = enemy.rect.centerx
            wy = enemy.rect.top - 4
            self._ftm.add_damage(final_dmg, wx, wy, is_crit=is_backstab)

        # 8. 音效事件
        _post_hit_sound("hit_flesh")
