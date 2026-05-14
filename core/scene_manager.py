# =============================================================
# core/scene_manager.py —— 场景管理器（栈式）
# =============================================================

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, List, Tuple, Optional

if TYPE_CHECKING:
    from scenes.base_scene import BaseScene

logger = logging.getLogger(__name__)


class SceneManager:
    """
    栈式场景管理器。

    - push(scene)    ：将新场景压入栈顶（旧场景暂停但不销毁，适合暂停菜单叠加）
    - pop()          ：弹出栈顶场景，恢复下方场景
    - replace(scene) ：替换栈顶（销毁当前场景，适合关卡切换）
    - clear_and_push ：清空栈后压入新场景（回主菜单等）

    每帧由 Game 驱动：
        update(dt)    → 栈顶场景 update
        render(renderer) → 从底到顶依次 render（透明叠加）
        handle_events(events) → 栈顶场景处理事件
    """

    def __init__(self):
        self._stack: List["BaseScene"] = []
        self._pending: List[Tuple[str, Optional["BaseScene"]]] = []

    # ---- 延迟操作（避免在 update 中途修改栈） ----

    def push(self, scene: "BaseScene"):
        """压栈（帧末生效）"""
        self._pending.append(("push", scene))

    def pop(self):
        """弹栈（帧末生效）"""
        self._pending.append(("pop", None))

    def replace(self, scene: "BaseScene"):
        """替换栈顶（帧末生效）"""
        self._pending.append(("replace", scene))

    def clear_and_push(self, scene: "BaseScene"):
        """清空栈并压入新场景（帧末生效）"""
        self._pending.append(("clear_push", scene))

    # ---- 每帧驱动 ----

    def apply_pending(self):
        """帧末处理所有挂起的场景操作，由 Game 在每帧末调用"""
        if not self._pending:
            return
        for op, scene in self._pending:
            self._apply(op, scene)
        self._pending.clear()

    def _apply(self, op: str, scene: "BaseScene | None"):
        if op == "push":
            if self._stack:
                self._stack[-1].on_pause()
            self._stack.append(scene)
            scene.on_enter()
            logger.debug("SceneManager: push -> '%s'", scene.__class__.__name__)

        elif op == "pop":
            if self._stack:
                top = self._stack.pop()
                top.on_exit()
                if self._stack:
                    self._stack[-1].on_resume()
                logger.debug("SceneManager: pop '%s'", top.__class__.__name__)

        elif op == "replace":
            if self._stack:
                top = self._stack.pop()
                top.on_exit()
            self._stack.append(scene)
            scene.on_enter()
            logger.debug("SceneManager: replace -> '%s'", scene.__class__.__name__)

        elif op == "clear_push":
            while self._stack:
                self._stack.pop().on_exit()
            self._stack.append(scene)
            scene.on_enter()
            logger.debug("SceneManager: clear_and_push -> '%s'",
                         scene.__class__.__name__)

    def update(self, dt: float):
        if self._stack:
            self._stack[-1].update(dt)

    def render(self, renderer):
        # 从底到顶渲染（支持透明叠加）
        for scene in self._stack:
            scene.render(renderer)

    def handle_events(self, events: list):
        if self._stack:
            self._stack[-1].handle_events(events)

    # ---- 查询 ----

    @property
    def current(self) -> Optional["BaseScene"]:
        return self._stack[-1] if self._stack else None

    @property
    def stack_size(self) -> int:
        return len(self._stack)

    def is_empty(self) -> bool:
        return len(self._stack) == 0


# 全局单例
scene_manager = SceneManager()
