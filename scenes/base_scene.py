# =============================================================
# scenes/base_scene.py —— 场景基类
# =============================================================

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.renderer import Renderer


class BaseScene:
    """
    所有场景的基类。
    SceneManager 管理的场景都必须继承此类。
    """

    def on_enter(self):
        """场景被压入栈顶（第一次进入或从暂停恢复到顶部）时调用"""
        pass

    def on_exit(self):
        """场景被弹出/替换时调用（销毁前的清理）"""
        pass

    def on_pause(self):
        """场景被压入其他场景下方（暂停，但不销毁）时调用"""
        pass

    def on_resume(self):
        """场景重新回到栈顶（从暂停恢复）时调用"""
        pass

    def update(self, dt: float):
        """每帧逻辑更新，dt 单位秒"""
        pass

    def render(self, renderer: "Renderer"):
        """每帧渲染，向 renderer 提交绘制命令"""
        pass

    def handle_events(self, events: list):
        """处理本帧的 pygame 事件列表"""
        pass
