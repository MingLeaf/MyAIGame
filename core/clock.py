# =============================================================
# core/clock.py —— 游戏时钟，管理 delta_time 与帧率
# =============================================================

import pygame
from config import FPS_TARGET


class GameClock:
    """
    封装 pygame.time.Clock，提供：
    - delta_time（秒）：上一帧耗时，用于帧率无关的物理/动画计算
    - fps：当前平均帧率
    - total_time：游戏运行总时间（秒）
    - tick()：每帧调用，限制帧率并更新以上数值
    """

    def __init__(self, fps_limit: int = FPS_TARGET):
        self._clock      = pygame.time.Clock()
        self._fps_limit  = fps_limit
        self._dt         = 0.0
        self._total      = 0.0
        self._frame_count = 0

    def tick(self):
        """
        每帧调用一次。
        限制帧率并更新 delta_time。
        返回 delta_time（秒）。
        """
        ms = self._clock.tick(self._fps_limit)
        # 限制最大 dt，防止调试暂停后出现巨型跳步
        self._dt = min(ms / 1000.0, 0.05)
        self._total += self._dt
        self._frame_count += 1
        return self._dt

    # ---- 属性 ----

    @property
    def delta_time(self) -> float:
        """上一帧耗时，单位秒"""
        return self._dt

    @property
    def fps(self) -> float:
        """当前平均帧率"""
        return self._clock.get_fps()

    @property
    def total_time(self) -> float:
        """游戏运行总时间，单位秒"""
        return self._total

    @property
    def frame_count(self) -> int:
        """已渲染帧数"""
        return self._frame_count

    @property
    def fps_limit(self) -> int:
        return self._fps_limit

    @fps_limit.setter
    def fps_limit(self, value: int):
        self._fps_limit = value
