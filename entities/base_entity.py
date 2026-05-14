# =============================================================
# entities/base_entity.py —— 实体基类（位置 / 碰撞箱 / 生命周期）
# =============================================================

from __future__ import annotations
from typing import Optional, Tuple
import pygame

import utils.debug as debug
from utils.color import DEBUG_HITBOX


class BaseEntity:
    """
    游戏世界中所有对象的基类（玩家、敌人、NPC 等均继承此类）。
    提供：
    - 世界坐标位置 (x, y)
    - 碰撞矩形（相对于中心点偏移）
    - 生命周期标记（active / dead）
    - 基本 update / render 接口
    """

    def __init__(self,
                 x: float, y: float,
                 width: int, height: int,
                 hitbox_offset: Tuple[int, int] = (0, 0)):
        """
        :param x, y:           实体中心点世界坐标
        :param width, height:  碰撞矩形尺寸
        :param hitbox_offset:  碰撞矩形相对中心点的偏移
        """
        self.x: float = x
        self.y: float = y

        self._hb_w      = width
        self._hb_h      = height
        self._hb_offset = hitbox_offset  # (ox, oy)

        self.active: bool = True
        self.dead:   bool = False

        # 速度（像素/秒）
        self.vel_x: float = 0.0
        self.vel_y: float = 0.0

        # 朝向：1 = 右，-1 = 左
        self.facing: int = 1

    # ---- 碰撞矩形 ----

    @property
    def rect(self) -> pygame.Rect:
        """返回当前碰撞矩形（世界坐标）"""
        ox, oy = self._hb_offset
        return pygame.Rect(
            int(self.x) - self._hb_w // 2 + ox,
            int(self.y) - self._hb_h  + oy,
            self._hb_w,
            self._hb_h,
        )

    @rect.setter
    def rect(self, new_rect: pygame.Rect):
        """通过矩形反向更新 x, y（移动解算后同步位置用）"""
        ox, oy = self._hb_offset
        self.x = float(new_rect.x + self._hb_w // 2 - ox)
        self.y = float(new_rect.y + self._hb_h - oy)

    # ---- 生命周期 ----

    def update(self, dt: float):
        """每帧逻辑更新（子类重写）"""
        pass

    def render(self, surface: pygame.Surface, cam_offset: Tuple[int, int]):
        """
        渲染（子类重写）。
        cam_offset: (cam_x, cam_y) 摄像机偏移
        """
        pass

    def on_death(self):
        """死亡时调用（子类重写）"""
        self.dead   = True
        self.active = False

    def destroy(self):
        """立即销毁（从实体列表移除前调用）"""
        self.active = False

    # ---- 位置工具 ----

    def set_position(self, x: float, y: float):
        self.x = x
        self.y = y

    def move(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    def distance_to(self, other: "BaseEntity") -> float:
        import math
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def distance_to_point(self, px: float, py: float) -> float:
        import math
        return math.sqrt((self.x - px) ** 2 + (self.y - py) ** 2)

    # ---- 调试渲染 ----

    def render_debug(self, surface: pygame.Surface, cam_offset: Tuple[int, int]):
        """在调试模式下绘制碰撞框"""
        if not debug.enabled or not debug.show_hitbox:
            return
        screen_rect = self.rect.move(-cam_offset[0], -cam_offset[1])
        debug.draw_rect(surface, screen_rect, DEBUG_HITBOX)

    def __repr__(self):
        return (f"<{self.__class__.__name__} "
                f"pos=({self.x:.0f},{self.y:.0f}) "
                f"active={self.active}>")
