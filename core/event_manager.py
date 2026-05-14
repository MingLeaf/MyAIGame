# =============================================================
# core/event_manager.py —— 全局事件总线（发布-订阅模式）
# =============================================================

from typing import Callable, Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class EventManager:
    """
    全局事件总线，用于解耦各模块间通信。

    用法：
        # 订阅
        event_manager.subscribe("player_death", my_callback)

        # 发布
        event_manager.emit("player_death", {"position": (100, 200)})

        # 取消订阅
        event_manager.unsubscribe("player_death", my_callback)
    """

    def __init__(self):
        # { event_name: [callback, ...] }
        self._listeners: Dict[str, List[Callable]] = {}
        # 延迟发布队列：[(event_name, data), ...]
        self._deferred: List[Tuple[str, dict]] = []

    # ---- 订阅 / 取消 ----

    def subscribe(self, event: str, callback: Callable):
        """订阅事件"""
        if event not in self._listeners:
            self._listeners[event] = []
        if callback not in self._listeners[event]:
            self._listeners[event].append(callback)

    def on(self, event: str, callback: Callable):
        """subscribe 的简洁别名，支持链式风格注册。"""
        self.subscribe(event, callback)
        return self   # 返回 self 允许链式调用

    def unsubscribe(self, event: str, callback: Callable):
        """取消订阅"""
        if event in self._listeners:
            try:
                self._listeners[event].remove(callback)
            except ValueError:
                pass

    def unsubscribe_all(self, event: str):
        """清除某个事件的所有订阅"""
        self._listeners.pop(event, None)

    def clear(self):
        """清除全部订阅（场景切换时使用）"""
        self._listeners.clear()
        self._deferred.clear()

    # ---- 发布 ----

    def emit(self, event: str, data: Optional[dict] = None):
        """立即发布事件，同步调用所有订阅者"""
        if data is None:
            data = {}
        callbacks = self._listeners.get(event, [])
        for cb in list(callbacks):        # 列表副本防止回调内修改
            try:
                cb(data)
            except Exception as exc:
                logger.exception("EventManager: 事件 '%s' 回调异常: %s", event, exc)

    def emit_deferred(self, event: str, data: Optional[dict] = None):
        """
        延迟发布：将事件推入队列，下次调用 flush() 时统一触发。
        适合在 update 中触发、在帧末统一处理的场景。
        """
        self._deferred.append((event, data or {}))

    def flush(self):
        """处理所有延迟事件（每帧末尾调用一次）"""
        pending = self._deferred[:]
        self._deferred.clear()
        for event, data in pending:
            self.emit(event, data)

    # ---- 查询 ----

    def has_listeners(self, event: str) -> bool:
        return bool(self._listeners.get(event))

    def listener_count(self, event: str) -> int:
        return len(self._listeners.get(event, []))


# 全局单例
event_manager = EventManager()
