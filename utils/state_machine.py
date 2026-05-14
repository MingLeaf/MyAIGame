# =============================================================
# utils/state_machine.py —— 通用有限状态机基类
# =============================================================
from __future__ import annotations
from typing import Dict, Optional


class State:
    """
    单个状态基类，子类重写所需方法即可。
    """

    def __init__(self, name: str):
        self.name = name
        self.machine: Optional["StateMachine"] = None   # 由 StateMachine 注入

    def on_enter(self, prev_state: Optional["State"] = None):
        """进入该状态时调用"""
        pass

    def on_exit(self, next_state: Optional["State"] = None):
        """离开该状态时调用"""
        pass

    def update(self, dt: float):
        """每帧逻辑更新"""
        pass

    def handle_event(self, event) -> bool:
        """
        处理事件，返回 True 表示事件已消费（不再向上传递）。
        """
        return False

    def __repr__(self):
        return f"<State '{self.name}'>"


class StateMachine:
    """
    通用有限状态机。
    用法示例：
        sm = StateMachine(owner=self)
        sm.add_state(IdleState())
        sm.add_state(RunState())
        sm.change_state("Idle")
    """

    def __init__(self, owner=None):
        self.owner   = owner
        self._states: Dict[str, State] = {}
        self._current: Optional[State] = None
        self._previous: Optional[State] = None

    # ---- 注册 ----

    def add_state(self, state: State):
        """注册一个状态，同时将 machine 引用注入状态"""
        state.machine = self
        self._states[state.name] = state

    def add_states(self, *states: State):
        for s in states:
            self.add_state(s)

    # ---- 切换 ----

    def change_state(self, name: str, force: bool = False):
        """
        切换到指定状态。
        :param name:  目标状态名
        :param force: 为 True 时即使目标与当前相同也强制重入
        """
        if name not in self._states:
            raise KeyError(f"StateMachine: 未知状态 '{name}'")

        target = self._states[name]

        if not force and self._current is target:
            return

        prev = self._current
        if prev is not None:
            prev.on_exit(target)

        self._previous = prev
        self._current  = target
        self._current.on_enter(prev)

    # ---- 驱动 ----

    def update(self, dt: float):
        if self._current is not None:
            self._current.update(dt)

    def handle_event(self, event) -> bool:
        if self._current is not None:
            return self._current.handle_event(event)
        return False

    # ---- 查询 ----

    @property
    def current(self) -> Optional[State]:
        return self._current

    @property
    def current_name(self) -> str:
        return self._current.name if self._current else ""

    @property
    def previous(self) -> Optional[State]:
        return self._previous

    def is_in(self, *names: str) -> bool:
        """判断当前是否处于给定名称之一的状态"""
        return self.current_name in names

    def has_state(self, name: str) -> bool:
        return name in self._states

    def __repr__(self):
        return (f"<StateMachine current='{self.current_name}' "
                f"states={list(self._states.keys())}>")
