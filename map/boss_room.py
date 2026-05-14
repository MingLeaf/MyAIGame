# =============================================================
# map/boss_room.py —— Boss 房间（雾门 + 关门 + Boss 血条触发）
#
# 第 9 阶段：放置在地图上的 Boss 房间触发器。
#
# 设计：
#   - BossRoom 是一个不可通过的"雾门"实体
#   - 玩家走入雾门范围 → 触发 boss_room_enter 事件
#   - GameScene 监听此事件 → push BossScene
#   - BossScene 接管渲染，显示 Boss 血条
# =============================================================
from __future__ import annotations
import pygame
import math
import random

from utils.color import UI_HIGHLIGHT, WHITE
from utils.timer import Timer
from core.event_manager import event_manager
from ui.font_manager import get_font


class BossRoom:
    """
    雾门触发器。

    属性：
        rect:           碰撞矩形（入口）
        boss_id:        关联的 Boss ID
        boss_class:     Boss 类引用（如 DukeRotbone）
        spawn_x, spawn_y: Boss 出生位置（世界坐标）
    """

    TRIGGER_WIDTH = 64
    TRIGGER_HEIGHT = 128

    def __init__(self, room_id: str,
                 world_x: float, world_y: float,
                 boss_id: str, boss_class,
                 spawn_x: float = 0, spawn_y: float = 0):
        self.room_id   = room_id
        self.x         = world_x
        self.y         = world_y
        self.boss_id   = boss_id
        self.boss_cls  = boss_class
        self.spawn_x   = spawn_x if spawn_x else world_x + 200
        self.spawn_y   = spawn_y if spawn_y else world_y - 32

        # 雾门粒子动画
        self._anim_timer = Timer(0.08, auto_reset=True)
        self._particles: list[list] = []  # [[x, y, vx, vy, life, color], ...]
        self._generate_particles()

        # 碰撞矩形
        tw, th = self.TRIGGER_WIDTH, self.TRIGGER_HEIGHT
        self.rect = pygame.Rect(
            int(self.x) - tw // 2,
            int(self.y) - th,
            tw, th,
        )
        self.trigger_rect = pygame.Rect(
            int(self.x) - tw,
            int(self.y) - th,
            tw * 2, th,
        )

    def _generate_particles(self) -> None:
        """生成雾门粒子。"""
        tw, th = self.TRIGGER_WIDTH, self.TRIGGER_HEIGHT
        for _ in range(40):
            self._particles.append([
                random.uniform(-tw, tw),
                random.uniform(-th, 0),
                random.uniform(-20, 20),
                random.uniform(-30, -5),
                random.uniform(0.6, 2.0),
                (140, 160, 200) if random.random() > 0.5 else (180, 200, 240),
            ])

    # ----------------------------------------------------------------
    # 更新
    # ----------------------------------------------------------------

    def update(self, dt: float, player_rect: pygame.Rect) -> bool:
        """
        每帧更新粒子雾门。
        返回 True 表示玩家进入了雾门范围。
        """
        self._anim_timer.update(dt)

        tw, th = self.TRIGGER_WIDTH, self.TRIGGER_HEIGHT
        for p in self._particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] <= 0 or p[1] < -th - 20:
                p[0] = random.uniform(-tw, tw)
                p[1] = 0
                p[2] = random.uniform(-20, 20)
                p[3] = random.uniform(-30, -5)
                p[4] = random.uniform(0.6, 2.0)

        # 玩家进入检测
        return self.trigger_rect.colliderect(player_rect)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        ox, oy = cam_offset
        sx = int(self.x) - ox
        sy = int(self.y) - oy

        # 雾门主体半透明
        tw, th = self.TRIGGER_WIDTH, self.TRIGGER_HEIGHT
        gate_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
        gate_surf.fill((80, 100, 140, 60))
        surface.blit(gate_surf, (sx - tw // 2, sy - th))

        # 粒子
        for p in self._particles:
            px = sx + int(p[0])
            py = sy + int(p[1])
            alpha = int(min(255, 200 * p[4]))
            color = (*p[5], alpha)
            try:
                dot = pygame.Surface((4, 4), pygame.SRCALPHA)
                dot.fill(color)
                surface.blit(dot, (px - 2, py - 2))
            except Exception:
                pass

        # 门框
        pygame.draw.rect(surface, (100, 120, 160),
                         (sx - tw // 2, sy - th, tw, th), 2)

        # 交互提示
        font = get_font(16)
        hint = font.render("穿越雾门", True, (200, 210, 230))
        surface.blit(hint, hint.get_rect(center=(sx, sy - th - 12)))


__all__ = ["BossRoom"]
