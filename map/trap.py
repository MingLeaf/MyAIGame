# =============================================================
# map/trap.py —— 环境陷阱（刺墙 / 坠石 / 燃烧地面）
# =============================================================

from __future__ import annotations
from enum import Enum
from typing import Optional
import pygame

from utils.timer import Timer


class TrapType(Enum):
    SPIKE       = "spike"       # 静态刺墙，持续伤害
    FALLING_ROCK= "falling_rock"# 坠石，被触发后延迟坠落
    FIRE_GROUND = "fire_ground" # 燃烧地面，周期性激活


class Trap:
    """
    环境陷阱基类。
    每帧调用 update(dt) 更新状态；
    调用 check_entity(entity_rect) 判断是否触发并返回伤害。
    """

    def __init__(self,
                 trap_type: TrapType,
                 rect: pygame.Rect,
                 damage: int = 10,
                 damage_type: str = "physical",
                 trigger_once: bool = False):
        self.trap_type   = trap_type
        self.rect        = rect
        self.damage      = damage
        self.damage_type = damage_type
        self.trigger_once= trigger_once
        self.active      = True
        self.triggered   = False
        self._cooldown   = Timer(1.0, auto_reset=True)  # 伤害间隔 1s

    def update(self, dt: float):
        if self.active:
            self._cooldown.update(dt)

    def check_entity(self, entity_rect: pygame.Rect) -> int:
        """
        检测实体是否触碰陷阱。
        返回本次造成的伤害值（0=无伤害）。
        """
        if not self.active:
            return 0
        if not self.rect.colliderect(entity_rect):
            return 0
        if not self._cooldown.is_finished():
            return 0
        self._cooldown.start()
        if self.trigger_once:
            self.active = False
        return self.damage

    def render_debug(self, surface: pygame.Surface, cam_offset: tuple):
        """调试模式绘制陷阱轮廓"""
        draw_rect = self.rect.move(-cam_offset[0], -cam_offset[1])
        color = (220, 50, 50) if self.active else (80, 80, 80)
        pygame.draw.rect(surface, color, draw_rect, 2)


class FallingRockTrap(Trap):
    """
    坠石陷阱：玩家进入触发区域后，延迟一段时间开始下落。
    """

    def __init__(self, rect: pygame.Rect, trigger_rect: pygame.Rect,
                 delay: float = 0.8, fall_speed: float = 400):
        super().__init__(TrapType.FALLING_ROCK, rect,
                         damage=30, damage_type="physical")
        self.trigger_rect  = trigger_rect
        self._delay_timer  = Timer(delay)
        self._fall_speed   = fall_speed
        self._falling      = False
        self._origin_y     = float(rect.y)

    def update(self, dt: float):
        super().update(dt)
        if self._falling:
            self.rect.y += int(self._fall_speed * dt)
        elif self._delay_timer.is_running():
            self._delay_timer.update(dt)
            if self._delay_timer.is_finished():
                self._falling = True

    def check_trigger(self, entity_rect: pygame.Rect):
        """当玩家进入触发区域时开始计时"""
        if (not self._falling and not self._delay_timer.is_running()
                and self.trigger_rect.colliderect(entity_rect)):
            self._delay_timer.start()

    def reset(self):
        self.rect.y    = int(self._origin_y)
        self._falling  = False
        self._delay_timer.reset()
        self.active    = True
