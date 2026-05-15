# =============================================================
# animation/animation_state_machine.py —— 动画状态机
#
# 将实体状态机中的状态名映射到 AnimationClip。
# 实体切换状态（如 Idle→Run→Attack）时，动画状态机自动切换对应动画。
#
# 与 utils/state_machine.py 的关系：
#   - AnimationStateMachine 是动画层的状态机，不代替实体 FSM
#   - 它只负责"哪个状态→播放哪段动画"的映射
#   - 实体 FSM 切换状态后 → 调用 asm.set_state(new_state) 即可
#
# 接口（供 Animator 调用）：
#   - set_state(state_name) → 切换到对应动画
#   - get_clip() → 返回当前 AnimationClip
#   - update(dt) → 推进当前动画
# =============================================================
from __future__ import annotations

from typing import Dict, Optional
from animation.animation_clip import AnimationClip


class AnimationStateMachine:
    """
    动画状态机。

    用法：
        asm = AnimationStateMachine()
        asm.register("idle",  AnimationClip.placeholder(...))
        asm.register("walk",   AnimationClip.placeholder(...))
        asm.register("attack", AnimationClip.placeholder(...))

        # 每帧：
        asm.set_state(entity.fsm.current)   # 与实体 FSM 同步
        clip = asm.get_clip()
        surf, frame_idx = clip.get_frame(asm.elapsed)
    """

    def __init__(self):
        # 状态名 → AnimationClip
        self._clips: Dict[str, AnimationClip] = {}
        # 当前状态
        self._current: str = ""
        # 当前状态已持续的时间（秒），自动随 update 推进
        self.elapsed: float = 0.0
        # 播放完毕回调（不循环动画结束时触发一次）
        self._on_finished_callback = None

    # ----------------------------------------------------------------
    # 注册与配置
    # ----------------------------------------------------------------

    def register(self, state_name: str, clip: AnimationClip) -> None:
        """
        注册一个状态对应的动画。

        :param state_name: 实体 FSM 状态名（如 "Idle", "Run", "Attack"）
        :param clip:       对应的 AnimationClip
        """
        self._clips[state_name] = clip
        if not self._current:
            self._current = state_name

    def register_placeholder(self,
                             state_name: str,
                             frame_count: int = 4,
                             frame_rate: float = 12.0,
                             size: tuple = (64, 64),
                             color: tuple = (180, 180, 180),
                             loop: bool = True) -> None:
        """便捷方法：用占位图注册一个状态。"""
        clip = AnimationClip.placeholder(
            frame_count=frame_count,
            frame_rate=frame_rate,
            size=size,
            color=color,
            loop=loop,
            name=state_name,
        )
        self.register(state_name, clip)

    def unregister(self, state_name: str) -> None:
        """移除状态映射。"""
        self._clips.pop(state_name, None)
        if self._current == state_name:
            self._current = next(iter(self._clips), "")

    # ----------------------------------------------------------------
    # 状态切换
    # ----------------------------------------------------------------

    def set_state(self, state_name: str) -> None:
        """
        切换到指定状态的动画。若状态未注册，保持当前动画不变。

        同状态不重置时间（避免每帧 set_state 导致动画卡在第一帧）。
        """
        if state_name == self._current:
            return
        if state_name in self._clips:
            self._current = state_name
            self.elapsed = 0.0

    def force_reset(self) -> None:
        """强制重置当前动画（用于连段等需要从头播放的场景）。"""
        self.elapsed = 0.0

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    def get_clip(self) -> Optional[AnimationClip]:
        """返回当前正在播放的 AnimationClip。"""
        return self._clips.get(self._current)

    def get_current_state(self) -> str:
        return self._current

    def has_state(self, state_name: str) -> bool:
        return state_name in self._clips

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        """推进当前动画时间 + 检测播放结束。"""
        self.elapsed += dt

        clip = self.get_clip()
        if clip is not None and clip.is_finished(self.elapsed):
            self._on_clip_finished()

    def on_finished(self, callback) -> None:
        """设置动画播放完毕回调（用于 Attack → Idle 自动切回）。"""
        self._on_finished_callback = callback

    def _on_clip_finished(self) -> None:
        if self._on_finished_callback:
            self._on_finished_callback(self._current)

    # ----------------------------------------------------------------
    # 从配置字典批量注册（数据驱动）
    # ----------------------------------------------------------------

    def load_from_config(self, config: dict) -> None:
        """
        从字典批量注册占位动画。

        config 格式：
            {
                "Idle":  {"frames": 4, "fps": 8,  "color": [180,180,180]},
                "Walk":  {"frames": 8, "fps": 12, "color": [120,180,120]},
                "Hurt":  {"frames": 2, "fps": 8,  "color": [220,60,60], "loop": false},
            }
        """
        for state_name, params in config.items():
            self.register_placeholder(
                state_name=state_name,
                frame_count=params.get("frames", 4),
                frame_rate=params.get("fps", 12.0),
                size=tuple(params.get("size", (64, 64))),
                color=tuple(params.get("color", (180, 180, 180))),
                loop=params.get("loop", True),
            )

    def __repr__(self) -> str:
        return (f"<AnimationStateMachine current='{self._current}' "
                f"states={list(self._clips.keys())}>")
