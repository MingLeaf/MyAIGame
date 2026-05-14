# =============================================================
# combat/combo_system.py —— 攻击连段系统
#
# 设计：
#   把「轻攻击 1 → 2 → 3」这种连段输入窗口的判定独立成
#   ComboWindow 组件，攻击状态只需 push_input / consume_next，
#   即可获得下一段攻击名（或 None 表示连段结束）。
#
# 复用：
#   - 玩家不同武器有不同连段链（剑：3 段；大剑：2 段；匕首：4 段）
#   - 后续可扩展「轻轻重」混合连段
#   - ComboChain 完全数据驱动，不耦合具体武器实现
# =============================================================
from __future__ import annotations

from typing import List, Optional


class ComboChain:
    """
    一条线性连段链。
    例：ComboChain(["LightAttack1", "LightAttack2", "LightAttack3"])
    表示连段顺序：1 → 2 → 3，且 3 段后无后续。
    """

    def __init__(self, steps: List[str]):
        if not steps:
            raise ValueError("ComboChain steps cannot be empty")
        self._steps: List[str] = list(steps)

    def get(self, index: int) -> Optional[str]:
        """获取第 index 段动作名。越界返回 None。"""
        if 0 <= index < len(self._steps):
            return self._steps[index]
        return None

    def next_after(self, current: str) -> Optional[str]:
        """根据当前段名查找下一段。"""
        try:
            idx = self._steps.index(current)
        except ValueError:
            return None
        return self.get(idx + 1)

    @property
    def length(self) -> int:
        return len(self._steps)

    def __repr__(self) -> str:
        return f"<ComboChain {' -> '.join(self._steps)}>"


# ----------------------------------------------------------------
# 默认连段链（武器未指定时使用）
# ----------------------------------------------------------------
DEFAULT_LIGHT_CHAIN = ComboChain(["LightAttack1", "LightAttack2", "LightAttack3"])


class ComboWindow:
    """
    连段窗口检测器（绑定到「单次攻击状态」生命周期）。

    工作流程：
        1. 进入攻击状态时 reset(chain, current_step_name)
        2. 攻击播放过程中（特别是后摇阶段）每帧调用 push_input(pressed)
           把玩家是否按下了下一段攻击键告知本组件
        3. 状态结束时 consume_next() 返回下一段动作名
           （或 None 表示无连段输入 / 已是最后一段）

    同时记录窗口期：仅当 frame ≥ window_open_frame 时才接受输入，
    防止前摇阶段的连按提前进入下一段。
    """

    def __init__(self):
        self._chain:        Optional[ComboChain] = None
        self._current_name: str  = ""
        self._frame:        int  = 0
        self._window_open:  int  = 0   # 第几帧后开始接受连段输入
        self._buffered:     bool = False

    # ----------------------------------------------------------------
    # 控制接口
    # ----------------------------------------------------------------

    def reset(self,
              chain: ComboChain,
              current_name: str,
              window_open_frame: int) -> None:
        """攻击状态进入时调用。"""
        self._chain        = chain
        self._current_name = current_name
        self._frame        = 0
        self._window_open  = max(0, window_open_frame)
        self._buffered     = False

    def tick(self) -> None:
        """每帧调用一次（在 push_input 之前）。"""
        self._frame += 1

    def push_input(self, pressed: bool) -> None:
        """
        提交本帧是否检测到「连段输入」（玩家按下了攻击键）。
        只有窗口打开后才会被采纳。
        """
        if not pressed:
            return
        if self._frame >= self._window_open:
            self._buffered = True

    def consume_next(self) -> Optional[str]:
        """
        在攻击状态结束时调用：
          - 若曾有连段输入，则返回下一段动作名（可能为 None 表示链尾）
          - 若无输入则返回 None
        """
        if not self._buffered or self._chain is None:
            return None
        return self._chain.next_after(self._current_name)

    # ----------------------------------------------------------------
    # 状态查询
    # ----------------------------------------------------------------

    @property
    def has_buffered_input(self) -> bool:
        return self._buffered

    @property
    def window_open(self) -> bool:
        return self._frame >= self._window_open

    @property
    def current_frame(self) -> int:
        return self._frame

    def __repr__(self) -> str:
        return (f"<ComboWindow current={self._current_name} "
                f"frame={self._frame} window>={self._window_open} "
                f"buf={self._buffered}>")
