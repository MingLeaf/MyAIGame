# =============================================================
# entities/enemy/types/archer.py —— 弓箭手
#
# 数据来源：data/entities/enemies/archer.json
#
# AI 特征（覆盖 Chase 行为）：
#   - 在 max_attack_distance 内 + ideal_distance 外 → 站定射击（windup→active→cooldown）
#   - 玩家逼近到 min_keep_distance 内 → 后撤拉距（kite_speed_factor）
#   - 射击通过 area.projectiles 加入 Arrow 抛射物
# 不进入近战 Attack 状态（attack_range 在 JSON 中故意设得很大并由远程射击优先消耗）
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for, load_enemy_data,
)
from physics.projectile import Arrow

if TYPE_CHECKING:
    from map.collision_map import CollisionMap


# 远程攻击三段计时由 self._shoot_phase / self._shoot_frame 实现，
# 不依赖独立的 State，让远程攻击与 Chase 状态融合（避免被 EnemyAttackState 卡死）。
PHASE_NONE     = 0
PHASE_WINDUP   = 1
PHASE_ACTIVE   = 2
PHASE_COOLDOWN = 3


class Archer(BaseEnemy):
    """腐骨射手 / 精灵游侠。"""

    CATEGORY = "archer"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

        cfg = load_enemy_data(self.CATEGORY).get("ranged", {})
        self._cfg = cfg
        self.min_keep_distance:   float = float(cfg.get("min_keep_distance",   140.0))
        self.ideal_distance:      float = float(cfg.get("ideal_distance",      220.0))
        self.max_attack_distance: float = float(cfg.get("max_attack_distance", 320.0))
        self.shoot_windup:        int   = int(cfg.get("shoot_windup",   28))
        self.shoot_active:        int   = int(cfg.get("shoot_active",    2))
        self.shoot_cooldown:      int   = int(cfg.get("shoot_cooldown", 22))
        self.projectile_damage:   int   = int(cfg.get("projectile_damage", 16))
        self.projectile_speed:    float = float(cfg.get("projectile_speed",  520.0))
        self.kite_speed_factor:   float = float(cfg.get("kite_speed_factor",   0.85))

        # 射击三段计时
        self._shoot_phase: int = PHASE_NONE
        self._shoot_frame: int = 0
        self._shot_done:   bool = False

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)

    # ------------------------------------------------------------------
    # 远程攻击钩子：在 EnemyChaseState.update 中调用
    # 返回 True = 已接管本帧逻辑（Chase 不再继续 move/jump）
    # ------------------------------------------------------------------

    def try_ranged_attack(self, dist: float) -> bool:
        # 玩家死亡或不可见时取消任何进行中的射击
        if self.player is None or self.player.is_dead:
            self._reset_shoot()
            return False

        # 朝向玩家
        self.facing = 1 if self.player.x > self.x else -1

        # 拉距：玩家太近 → 后撤
        if dist < self.min_keep_distance and self._shoot_phase != PHASE_ACTIVE:
            # 后撤时若有进行中的射击，作废重置（被压迫无法射）
            if self._shoot_phase != PHASE_NONE:
                self._reset_shoot()
            self.vel_x = -self.facing * self.stats.speed * self.kite_speed_factor
            return True   # 已处理（避免 Chase 继续追近）

        # 在最大射程外 → 让 Chase 继续追近
        if dist > self.max_attack_distance and self._shoot_phase == PHASE_NONE:
            return False

        # 进入"理想射距"或正在射击 → 站定 + 推进射击循环
        self.vel_x = 0.0
        self._tick_shoot()
        return True

    # ------------------------------------------------------------------
    # 内部：射击三段循环
    # ------------------------------------------------------------------

    def _tick_shoot(self) -> None:
        if self._shoot_phase == PHASE_NONE:
            self._shoot_phase = PHASE_WINDUP
            self._shoot_frame = 0
            self._shot_done   = False
            return

        self._shoot_frame += 1

        if self._shoot_phase == PHASE_WINDUP:
            if self._shoot_frame >= self.shoot_windup:
                self._shoot_phase = PHASE_ACTIVE
                self._shoot_frame = 0

        elif self._shoot_phase == PHASE_ACTIVE:
            if not self._shot_done:
                self._fire_arrow()
                self._shot_done = True
            if self._shoot_frame >= self.shoot_active:
                self._shoot_phase = PHASE_COOLDOWN
                self._shoot_frame = 0

        elif self._shoot_phase == PHASE_COOLDOWN:
            if self._shoot_frame >= self.shoot_cooldown:
                self._reset_shoot()

    def _reset_shoot(self) -> None:
        self._shoot_phase = PHASE_NONE
        self._shoot_frame = 0
        self._shot_done   = False

    def _fire_arrow(self) -> None:
        if self.player is None:
            return
        area = self._get_area()
        if area is None:
            return

        # 从弓箭手胸部位置发射，给点向上初速以更"自然"
        spawn_x = self.rect.centerx + self.facing * 14
        spawn_y = self.rect.centery - 4
        # 直接朝向玩家（带轻微弧线由重力提供）
        import math
        dx = self.player.rect.centerx - spawn_x
        dy = self.player.rect.centery - spawn_y
        dist = max(1.0, math.hypot(dx, dy))
        vx = self.projectile_speed * (dx / dist)
        vy = self.projectile_speed * (dy / dist) * 0.4   # 减小竖直分量
        arrow = Arrow(
            x = spawn_x, y = spawn_y,
            vx = vx, vy = vy,
            damage = self.projectile_damage,
            owner = self,
            poise_damage = 6.0,
            element = "physical",
            lifetime = 2.0,
        )
        area.projectiles.append(arrow)

    def _get_area(self):
        # 优先看 player.current_area（与 PlayerCombat / GameScene 对齐）
        if self.player is not None:
            area = getattr(self.player, "current_area", None)
            if area is not None and hasattr(area, "projectiles"):
                return area
        return None

    # ------------------------------------------------------------------
    # 受击中断：射击中被打断则取消
    # ------------------------------------------------------------------

    def take_damage(self, amount: int, knockback_dir: int = 0,
                    poise_damage: float = 10.0):
        # 在 active 之前被击中视作打断
        if self._shoot_phase in (PHASE_WINDUP,):
            self._reset_shoot()
        super().take_damage(amount, knockback_dir, poise_damage)

    # ------------------------------------------------------------------
    # 渲染：在攻击前摇时给一个"瞄准"标记（弓拉满）
    # ------------------------------------------------------------------

    def render(self, surface, cam_offset):
        super().render(surface, cam_offset)
        if self._shoot_phase != PHASE_NONE:
            self._render_aim_indicator(surface, cam_offset)

    def _render_aim_indicator(self, surface, cam_offset):
        import pygame
        ox, oy = cam_offset
        cx = self.rect.centerx - ox
        cy = self.rect.centery - oy
        # 指示色：windup→黄；active→红；cooldown→灰
        if self._shoot_phase == PHASE_WINDUP:
            color = (255, 220, 80)
        elif self._shoot_phase == PHASE_ACTIVE:
            color = (255, 80, 80)
        else:
            color = (160, 160, 160)
        # 横向短线段表示"瞄准方向"
        end_x = cx + self.facing * 28
        pygame.draw.line(surface, color, (cx, cy), (end_x, cy - 4), 2)
