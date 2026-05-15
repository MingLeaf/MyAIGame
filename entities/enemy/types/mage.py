# =============================================================
# entities/enemy/types/mage.py —— 法师
#
# 数据来源：data/entities/enemies/mage.json
#
# 特征：
#   - 长吟唱（cast_windup 帧）后释放 MagicBall
#   - 吟唱期间被攻击 → 进入硬直，吟唱被打断
#   - 头顶吟唱进度条可视化
#   - 玩家接近时后撤（吟唱中站定继续施法，不打断）
# =============================================================
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for, load_enemy_data,
)
from physics.projectile import MagicBall
from core.event_manager import event_manager

if TYPE_CHECKING:
    pass


# 吟唱阶段
CAST_NONE     = 0
CAST_WINDUP   = 1
CAST_ACTIVE   = 2
CAST_COOLDOWN = 3


class Mage(BaseEnemy):
    """黑袍术士 / 邪祭司。"""

    CATEGORY = "mage"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

        cfg = load_enemy_data(self.CATEGORY).get("cast", {})
        self._cfg = cfg
        self.element:              str   = cfg.get("element", "fire")
        self.min_keep_distance:    float = float(cfg.get("min_keep_distance",   160.0))
        self.ideal_distance:       float = float(cfg.get("ideal_distance",      220.0))
        self.max_attack_distance:  float = float(cfg.get("max_attack_distance", 300.0))
        self.cast_windup:          int   = int(cfg.get("cast_windup",   50))
        self.cast_active:          int   = int(cfg.get("cast_active",    2))
        self.cast_cooldown:        int   = int(cfg.get("cast_cooldown", 45))
        self.projectile_damage:    int   = int(cfg.get("projectile_damage", 22))
        self.projectile_speed:     float = float(cfg.get("projectile_speed",  320.0))
        self.interrupt_poise_dmg:  float = float(cfg.get("interrupt_poise_dmg", 6.0))

        self._cast_phase: int = CAST_NONE
        self._cast_frame: int = 0
        self._cast_done:  bool = False

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)

    # ------------------------------------------------------------------
    # 远程攻击钩子：在 EnemyChaseState.update 中调用
    # ------------------------------------------------------------------

    def try_ranged_attack(self, dist: float) -> bool:
        if self.player is None or self.player.is_dead:
            self._reset_cast()
            return False

        self.facing = 1 if self.player.x > self.x else -1

        # 玩家太近且未吟唱 → 高速后撤
        if dist < self.min_keep_distance and self._cast_phase == CAST_NONE:
            self.vel_x = -self.facing * self.stats.speed * 1.2
            return True

        # 玩家太近但正在吟唱 → 边后撤边继续施法（第 10 阶段改进）
        if dist < self.min_keep_distance and self._cast_phase != CAST_NONE:
            self.vel_x = -self.facing * self.stats.speed * 0.5
            self._tick_cast()
            return True

        if dist > self.max_attack_distance and self._cast_phase == CAST_NONE:
            return False

        # 站定吟唱
        self.vel_x = 0.0
        self._tick_cast()
        return True

    # ------------------------------------------------------------------
    # 吟唱循环
    # ------------------------------------------------------------------

    def _tick_cast(self) -> None:
        if self._cast_phase == CAST_NONE:
            self._cast_phase = CAST_WINDUP
            self._cast_frame = 0
            self._cast_done  = False
            event_manager.emit("mage_cast_start", {"enemy": self})
            return

        self._cast_frame += 1

        if self._cast_phase == CAST_WINDUP:
            if self._cast_frame >= self.cast_windup:
                self._cast_phase = CAST_ACTIVE
                self._cast_frame = 0

        elif self._cast_phase == CAST_ACTIVE:
            if not self._cast_done:
                self._fire_magic()
                self._cast_done = True
                event_manager.emit("mage_cast_release", {"enemy": self})
            if self._cast_frame >= self.cast_active:
                self._cast_phase = CAST_COOLDOWN
                self._cast_frame = 0

        elif self._cast_phase == CAST_COOLDOWN:
            if self._cast_frame >= self.cast_cooldown:
                self._reset_cast()

    def _reset_cast(self) -> None:
        was_casting = self._cast_phase != CAST_NONE
        self._cast_phase = CAST_NONE
        self._cast_frame = 0
        self._cast_done  = False
        if was_casting:
            event_manager.emit("mage_cast_cancel", {"enemy": self})

    def _fire_magic(self) -> None:
        if self.player is None:
            return
        area = self._get_area()
        if area is None:
            return

        spawn_x = self.rect.centerx + self.facing * 16
        spawn_y = self.rect.centery
        dx = self.player.rect.centerx - spawn_x
        dy = self.player.rect.centery - spawn_y
        dist = max(1.0, math.hypot(dx, dy))
        vx = self.projectile_speed * (dx / dist)
        vy = self.projectile_speed * (dy / dist) * 0.5

        ball = MagicBall(
            x = spawn_x, y = spawn_y,
            vx = vx, vy = vy,
            damage = self.projectile_damage,
            owner = self,
            element = self.element,
            poise_damage = 8.0,
            lifetime = 2.5,
        )
        area.projectiles.append(ball)

    def _get_area(self):
        if self.player is not None:
            area = getattr(self.player, "current_area", None)
            if area is not None and hasattr(area, "projectiles"):
                return area
        return None

    # ------------------------------------------------------------------
    # 受击：吟唱中被命中触发"被打断"事件
    # ------------------------------------------------------------------

    def take_damage(self, amount: int, knockback_dir: int = 0,
                    poise_damage: float = 10.0):
        was_casting = (self._cast_phase == CAST_WINDUP)
        # 吟唱被打断会额外消耗韧性
        if was_casting:
            poise_damage += self.interrupt_poise_dmg
            self._reset_cast()
            event_manager.emit("mage_cast_interrupted", {
                "enemy": self,
                "by_player": True,
            })
        super().take_damage(amount, knockback_dir, poise_damage)

    # ------------------------------------------------------------------
    # 渲染：吟唱进度条
    # ------------------------------------------------------------------

    def render(self, surface, cam_offset):
        super().render(surface, cam_offset)
        if self._cast_phase == CAST_WINDUP:
            self._render_cast_bar(surface, cam_offset)

    def _render_cast_bar(self, surface, cam_offset):
        import pygame
        ox, oy = cam_offset
        ratio = max(0.0, min(1.0, self._cast_frame / max(1, self.cast_windup)))
        bar_w = 40
        bar_h = 4
        bx = self.rect.centerx - bar_w // 2 - ox
        # 在血条 / 韧性条之上再叠一层
        by = self.rect.top - 22 - oy
        # 背景
        pygame.draw.rect(surface, (40, 30, 60), (bx, by, bar_w, bar_h))
        # 进度（紫色）
        filled = int(bar_w * ratio)
        if filled > 0:
            pygame.draw.rect(surface, (180, 80, 255),
                             (bx, by, filled, bar_h))
        # 边框
        pygame.draw.rect(surface, (220, 200, 255),
                         (bx, by, bar_w, bar_h), 1)
