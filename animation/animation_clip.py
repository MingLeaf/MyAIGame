# =============================================================
# animation/animation_clip.py —— 动画片段
#
# 一个 AnimationClip 描述一段动画的帧序列、播放速率、循环方式。
# 配合 Animator 使用，支持精灵表纹理或几何占位。
# =============================================================
from __future__ import annotations

from typing import List, Optional, Tuple
import pygame


class AnimationClip:
    """
    动画片段：持有帧列表和播放参数。

    属性：
      - frames:        pygame.Surface 列表（或 None 列表表示占位帧）
      - frame_rate:    每秒播放帧数
      - loop:          是否循环（True=循环, False=播放一次后停在最后一帧）
      - name:          片段名称（供 AnimationStateMachine 映射）

    占位模式：
      当 frames 为 None 或包含 None 元素时，通过 `render_placeholder`
      生成纯色矩形 + 边框（用于在没有资源时也能可视化验证）。

    接口：
      - get_frame(elapsed) → (Surface|None, int)   返回当前帧图 + 帧索引
      - is_finished(elapsed) → bool
      - duration → float                            总时长（秒）
    """

    def __init__(self,
                 frames: Optional[List[Optional[pygame.Surface]]] = None,
                 frame_rate: float = 12.0,
                 loop: bool = True,
                 name: str = ""):
        self.frames: List[Optional[pygame.Surface]] = frames or []
        self.frame_rate: float = max(1.0, frame_rate)
        self.loop: bool = loop
        self.name: str = name

        # ---- 占位渲染配置（当 frames 为空时使用） ----
        self._placeholder_size: Tuple[int, int] = (64, 64)
        self._placeholder_color: Tuple[int, int, int] = (180, 180, 180)
        self._placeholder_frame_count: int = 4

    # ----------------------------------------------------------------
    # 属性
    # ----------------------------------------------------------------

    @property
    def frame_count(self) -> int:
        return len(self.frames) if self.frames else self._placeholder_frame_count

    @property
    def duration(self) -> float:
        """总时长（秒）。"""
        if self.frame_count == 0 or self.frame_rate <= 0:
            return 0.0
        return self.frame_count / self.frame_rate

    @property
    def frame_interval(self) -> float:
        """每帧间隔（秒）。"""
        if self.frame_rate <= 0:
            return 0.1
        return 1.0 / self.frame_rate

    # ----------------------------------------------------------------
    # 帧查询
    # ----------------------------------------------------------------

    def get_frame(self, elapsed: float) -> Tuple[Optional[pygame.Surface], int]:
        """
        根据已播放时间返回当前帧。

        :param elapsed: 从动画开始已过的秒数
        :return: (surface, frame_index)
        """
        if self.frame_count == 0:
            return None, 0

        total_frames = self.frame_count
        frame_index = int(elapsed / self.frame_interval)

        if not self.loop:
            frame_index = min(frame_index, total_frames - 1)
        else:
            frame_index = frame_index % total_frames

        surf = None
        if self.frames and frame_index < len(self.frames):
            surf = self.frames[frame_index]

        if surf is None:
            surf = self._render_placeholder(frame_index)

        return surf, frame_index

    def is_finished(self, elapsed: float) -> bool:
        """不循环动画是否已播放完毕。"""
        if self.loop or self.frame_count == 0:
            return False
        return elapsed >= self.duration

    # ----------------------------------------------------------------
    # 占位渲染
    # ----------------------------------------------------------------

    def setup_placeholder(self,
                          size: Tuple[int, int] = (64, 64),
                          color: Tuple[int, int, int] = (180, 180, 180),
                          frame_count: int = 4) -> None:
        """配置占位帧的外观。"""
        self._placeholder_size = size
        self._placeholder_color = color
        self._placeholder_frame_count = max(1, frame_count)

    def _render_placeholder(self, frame_index: int) -> pygame.Surface:
        """生成一帧占位图形（带淡入淡出效果的色块）。"""
        w, h = self._placeholder_size
        r, g, b = self._placeholder_color

        # 用帧索引轻微改变亮度模拟动画
        ratio = (frame_index % max(1, self._placeholder_frame_count))
        ratio = ratio / max(1, self._placeholder_frame_count - 1) if self._placeholder_frame_count > 1 else 0.5
        # 亮度在 70%~100% 之间波动
        brightness = 0.7 + 0.3 * ratio
        color = (
            min(255, int(r * brightness)),
            min(255, int(g * brightness)),
            min(255, int(b * brightness)),
        )

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        # 圆角效果用实心圆近似
        center = (w // 2, h // 2)
        radius = min(w, h) // 3
        pygame.draw.circle(surf, color, center, radius)
        pygame.draw.circle(surf, (255, 255, 255, 80), center, radius, 1)
        return surf

    # ----------------------------------------------------------------
    # 工厂方法
    # ----------------------------------------------------------------

    @classmethod
    def placeholder(cls,
                    frame_count: int = 4,
                    frame_rate: float = 12.0,
                    size: Tuple[int, int] = (64, 64),
                    color: Tuple[int, int, int] = (180, 180, 180),
                    loop: bool = True,
                    name: str = "") -> "AnimationClip":
        """快速创建纯占位动画。"""
        clip = cls(frames=[], frame_rate=frame_rate, loop=loop, name=name)
        clip.setup_placeholder(size=size, color=color, frame_count=frame_count)
        return clip

    @classmethod
    def from_surfaces(cls,
                      surfaces: List[pygame.Surface],
                      frame_rate: float = 12.0,
                      loop: bool = True,
                      name: str = "") -> "AnimationClip":
        """从已有 Surface 列表创建。"""
        return cls(frames=surfaces, frame_rate=frame_rate, loop=loop, name=name)

    def __repr__(self) -> str:
        return (f"<AnimationClip '{self.name}' frames={self.frame_count} "
                f"fps={self.frame_rate:.0f} loop={self.loop}>")
