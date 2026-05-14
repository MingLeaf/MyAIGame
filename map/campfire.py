# =============================================================
# map/campfire.py —— 营地篝火对象（激活 / 传送 / 补充消耗品）
# =============================================================

from __future__ import annotations
import pygame

from utils.color import (COLOR_HP, UI_HIGHLIGHT, WHITE)
from utils.timer import Timer
from core.event_manager import event_manager
from ui.font_manager import get_font


class Campfire:
    """
    篝火对象。
    - 玩家靠近时显示交互提示
    - 玩家按交互键激活并保存为当前复活点
    - 激活后触发消耗品补充事件
    """

    INTERACT_RADIUS = 48    # 交互触发半径（像素）

    def __init__(self, campfire_id: str, world_x: float, world_y: float):
        self.campfire_id  = campfire_id
        self.x            = world_x
        self.y            = world_y
        self.activated    = False
        self._near_player = False

        # 火焰动画帧（占位：用颜色矩形模拟）
        self._anim_timer  = Timer(0.15, auto_reset=True)
        self._anim_frame  = 0
        self._anim_colors = [
            (220, 100, 20),
            (240, 140, 30),
            (255, 180, 50),
            (240, 120, 10),
        ]

        # 交互区域矩形（世界坐标）
        w, h = 32, 48
        self.rect = pygame.Rect(int(self.x) - w // 2,
                                int(self.y) - h, w, h)
        self.interact_rect = pygame.Rect(
            int(self.x) - self.INTERACT_RADIUS,
            int(self.y) - self.INTERACT_RADIUS * 2,
            self.INTERACT_RADIUS * 2,
            self.INTERACT_RADIUS * 2,
        )

    # ---- 更新 ----

    def update(self, dt: float, player_rect: pygame.Rect):
        """每帧更新：检测玩家是否在交互范围内，更新动画"""
        self._anim_timer.update(dt)
        if self._anim_timer.is_finished():
            self._anim_frame = (self._anim_frame + 1) % len(self._anim_colors)

        self._near_player = self.interact_rect.colliderect(player_rect)

    def try_activate(self, player_rect: pygame.Rect,
                      player=None, area=None) -> bool:
        """
        玩家按交互键时调用。
        若在范围内则激活篝火并发布事件，返回 True。

        第 8.1 阶段：
          - 首次激活：注册到 CampfireSystem（全局营地网络）
          - 不再自动触发休息（由 CampfireMenu 的"休息"选项显式触发）
          - 不重置敌人
        """
        if not self._near_player:
            return False

        was_activated = self.activated
        if not self.activated:
            self.activated = True

        # 注册到全局营地系统（传入 area_id 以便传送网络工作）
        area_id = ""
        if area is not None:
            area_id = getattr(area, "area_id", "")
        from systems.campfire_system import CampfireSystem
        CampfireSystem.activate(self.campfire_id, area_id, self.x, self.y)

        # 发布激活事件（不再自动触发休息/重置敌人）
        event_manager.emit("campfire_activated", {
            "campfire_id": self.campfire_id,
            "x": self.x,
            "y": self.y,
            "first_time": not was_activated,
        })
        return True

    # ---- 渲染 ----

    def render(self, surface: pygame.Surface, cam_offset: tuple):
        ox, oy = cam_offset
        sx = int(self.x) - ox
        sy = int(self.y) - oy

        # 底座
        pygame.draw.rect(surface, (80, 65, 50),
                         pygame.Rect(sx - 14, sy - 8, 28, 8))

        # 火焰（动画色块）
        color = self._anim_colors[self._anim_frame]
        pts = [
            (sx,      sy - 36),
            (sx - 10, sy - 16),
            (sx + 10, sy - 16),
        ]
        pygame.draw.polygon(surface, color, pts)
        inner_pts = [
            (sx,     sy - 28),
            (sx - 5, sy - 16),
            (sx + 5, sy - 16),
        ]
        pygame.draw.polygon(surface, (255, 240, 180), inner_pts)

        # 激活光环
        if self.activated:
            pygame.draw.circle(surface, (255, 200, 80, 60),
                               (sx, sy - 8), 20, 2)

        # 交互提示
        if self._near_player:
            font = get_font(22)
            hint = font.render("[F] 激活篝火", True, UI_HIGHLIGHT)
            surface.blit(hint, hint.get_rect(center=(sx, sy - 50)))
