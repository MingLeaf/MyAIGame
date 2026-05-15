# =============================================================
# animation/animator.py —— 动画控制器
#
# Animator 是动画系统的顶层外观，封装 AnimationStateMachine +
# 精灵表加载 + 占位回退。实体只需持有 Animator 并每帧调用
# update(dt) / render(surface, position)。
#
# 用法：
#     anim = Animator()
#     anim.register("Idle",  AnimationClip.placeholder(...))
#     anim.register("Run",   clip_run)
#     anim.set_state("Idle")
#
#     每帧：
#     anim.update(dt)
#     surf = anim.get_current_frame()
#     surface.blit(surf, (entity.x, entity.y))
#
# 未来接入真实精灵表：
#     anim.load_sprite_sheet("Idle", "assets/sprites/idle.png", rows=1, cols=4)
# =============================================================
from __future__ import annotations

from typing import Optional, Tuple
import pygame

from animation.animation_clip import AnimationClip
from animation.animation_state_machine import AnimationStateMachine
from animation.sprite_sheet_loader import SpriteSheetLoader


class Animator:
    """
    动画控制器。

    组合 AnimationStateMachine + SpriteSheetLoader，
    提供统一的动画注册、切换、更新、取帧接口。
    """

    def __init__(self):
        self._asm: AnimationStateMachine = AnimationStateMachine()
        self._loader: SpriteSheetLoader = SpriteSheetLoader()

        # 渲染参数
        self.flip_x: bool = False       # 是否水平翻转（跟随 facing）
        self.scale: float = 1.0         # 全局缩放
        self.offset: Tuple[int, int] = (0, 0)  # 渲染位置偏移（相对实体坐标）

    # ----------------------------------------------------------------
    # 注册动画
    # ----------------------------------------------------------------

    def register(self, state_name: str, clip: AnimationClip) -> None:
        """直接注册一个 AnimationClip。"""
        self._asm.register(state_name, clip)

    def register_placeholder(self,
                             state_name: str,
                             frame_count: int = 4,
                             frame_rate: float = 12.0,
                             size: tuple = (64, 64),
                             color: tuple = (180, 180, 180),
                             loop: bool = True) -> None:
        """用占位图形注册一个状态动画。"""
        self._asm.register_placeholder(
            state_name, frame_count, frame_rate, size, color, loop,
        )

    def load_sprite_sheet(self,
                          state_name: str,
                          path: str,
                          rows: int = 1,
                          cols: int = 1,
                          frame_width: int = 0,
                          frame_height: int = 0,
                          frame_rate: float = 12.0,
                          loop: bool = True,
                          colorkey: Optional[Tuple[int, int, int]] = None,
                          scale: float = 1.0) -> None:
        """
        从精灵表文件加载并注册一个状态动画。

        如果文件不存在或加载失败，自动回退为占位图形。
        """
        frames = self._loader.load(
            path, rows=rows, cols=cols,
            frame_width=frame_width, frame_height=frame_height,
            colorkey=colorkey, scale=scale,
        )
        if frames:
            clip = AnimationClip.from_surfaces(
                frames, frame_rate=frame_rate, loop=loop, name=state_name,
            )
        else:
            # 回退为占位
            clip = AnimationClip.placeholder(
                frame_count=rows * cols,
                frame_rate=frame_rate,
                loop=loop,
                name=state_name,
            )
        self._asm.register(state_name, clip)

    # ----------------------------------------------------------------
    # 状态控制
    # ----------------------------------------------------------------

    def set_state(self, state_name: str) -> None:
        """切换动画状态。同状态不重置时间。"""
        self._asm.set_state(state_name)

    def force_reset(self) -> None:
        """强制重置当前动画到第一帧。"""
        self._asm.force_reset()

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float, facing: int = 1) -> None:
        """
        推进动画时间。

        :param dt:     帧间隔（秒）
        :param facing: 实体朝向（+1 向右，-1 向左）
        """
        self._asm.update(dt)
        # 同步翻转：facing < 0 → flip_x = True
        self.flip_x = (facing < 0)

    # ----------------------------------------------------------------
    # 帧获取与渲染
    # ----------------------------------------------------------------

    def get_current_frame(self) -> Optional[pygame.Surface]:
        """
        返回当前动画帧的 Surface（未翻转）。

        若需水平翻转，调用 render() 或手动 flip_x 检测。
        """
        clip = self._asm.get_clip()
        if clip is None:
            return None
        surf, _ = clip.get_frame(self._asm.elapsed)
        return surf

    def get_current_frame_index(self) -> int:
        """返回当前帧索引（调试用）。"""
        clip = self._asm.get_clip()
        if clip is None:
            return 0
        _, idx = clip.get_frame(self._asm.elapsed)
        return idx

    def render(self,
               surface: pygame.Surface,
               x: int, y: int,
               centered: bool = True) -> None:
        """
        将当前帧绘制到目标 surface。

        :param surface: 目标画布
        :param x, y:    绘制锚点位置（centered=True 时为帧中心）
        :param centered: True=以帧中心对齐坐标；False=左上角对齐
        """
        frame = self.get_current_frame()
        if frame is None:
            return

        # 缩放
        if self.scale != 1.0:
            nw = max(1, int(frame.get_width() * self.scale))
            nh = max(1, int(frame.get_height() * self.scale))
            frame = pygame.transform.scale(frame, (nw, nh))

        # 翻转
        if self.flip_x:
            frame = pygame.transform.flip(frame, True, False)

        # 位置
        dx = x + self.offset[0]
        dy = y + self.offset[1]
        if centered:
            dx -= frame.get_width() // 2
            dy -= frame.get_height() // 2

        surface.blit(frame, (dx, dy))

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    @property
    def current_state(self) -> str:
        return self._asm.get_current_state()

    def is_finished(self) -> bool:
        """当前动画是否播放完毕（仅不循环时有意义）。"""
        clip = self._asm.get_clip()
        if clip is None:
            return True
        return clip.is_finished(self._asm.elapsed)

    def on_finished(self, callback) -> None:
        """设置动画播放完毕回调。"""
        self._asm.on_finished(callback)

    # ----------------------------------------------------------------
    # 批量配置
    # ----------------------------------------------------------------

    def load_from_config(self, config: dict) -> None:
        """从字典批量注册（同 AnimationStateMachine.load_from_config）。"""
        self._asm.load_from_config(config)

    def __repr__(self) -> str:
        return (f"<Animator state='{self.current_state}' "
                f"frame={self.get_current_frame_index()}>")
