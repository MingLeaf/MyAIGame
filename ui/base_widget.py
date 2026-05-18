# =============================================================
# ui/base_widget.py —— UI 控件基类
#
# 所有 UI 组件（HUD/背包/装备/死亡界面/营地菜单/对话框/商店等）
# 统一继承此类，提供：
#   - 位置尺寸管理（rect）
#   - 可见性控制（show/hide/toggle）
#   - 事件分发（handle_event）
#   - 更新/渲染接口（update/render）
#   - 鼠标悬停检测（is_hover）
#   - 层级管理（z_index）
# =============================================================
from __future__ import annotations
from typing import Optional, Tuple

import pygame


class BaseWidget:
    """
    UI 控件基类。

    典型子类集成（以 InventoryScreen 为例）：
        class InventoryScreen(BaseWidget):
            def __init__(self):
                super().__init__(rect=pygame.Rect(0, 0, 800, 600), z_index=50)
                self.is_open = False   # 子类自行管理开/关

            def handle_event(self, event) -> bool:
                if not self.visible:
                    return False
                # ... 处理鼠标/键盘
                return True

            def render(self, surface):
                if not self.visible:
                    return
                # ... 绘制
    """

    def __init__(self,
                 rect: Optional[pygame.Rect] = None,
                 visible: bool = False,
                 z_index: int = 40):
        """
        :param rect:    控件矩形区域（None 则默认全屏）
        :param visible: 初始可见性
        :param z_index: 渲染层级（参考 config.LAYER_*）
        """
        self.rect = rect or pygame.Rect(0, 0, 0, 0)
        self.visible = visible
        self.z_index = z_index

        # 是否消费事件（当 visible=True 时，handle_event 返回 True 会阻止事件继续传递）
        self._consumes_events = True

    # ----------------------------------------------------------------
    # 可见性控制
    # ----------------------------------------------------------------

    def show(self) -> None:
        """显示控件"""
        self.visible = True

    def hide(self) -> None:
        """隐藏控件"""
        self.visible = False

    def toggle(self) -> None:
        """切换可见性"""
        self.visible = not self.visible

    # ----------------------------------------------------------------
    # 每帧接口（子类覆写）
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        处理输入事件。
        :return: True 表示事件已被消耗，上层不应继续处理。
        """
        if not self.visible:
            return False
        return False

    def update(self, dt: float) -> None:
        """每帧更新（子类覆写实现动画/计时等）"""
        pass

    def render(self, surface: pygame.Surface) -> None:
        """每帧渲染（子类覆写实现绘制）"""
        pass

    # ----------------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------------

    def is_hover(self, mx: int, my: int) -> bool:
        """检测鼠标坐标是否在控件区域内"""
        return self.rect.collidepoint(mx, my)

    @property
    def center(self) -> Tuple[int, int]:
        return self.rect.center

    @center.setter
    def center(self, value: Tuple[int, int]):
        self.rect.center = value

    @property
    def x(self) -> int:
        return self.rect.x

    @x.setter
    def x(self, value: int):
        self.rect.x = value

    @property
    def y(self) -> int:
        return self.rect.y

    @y.setter
    def y(self, value: int):
        self.rect.y = value

    @property
    def width(self) -> int:
        return self.rect.width

    @width.setter
    def width(self, value: int):
        self.rect.width = value

    @property
    def height(self) -> int:
        return self.rect.height

    @height.setter
    def height(self, value: int):
        self.rect.height = value
