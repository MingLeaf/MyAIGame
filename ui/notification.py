# =============================================================
# ui/notification.py —— 浮动提示系统
#
# 管理屏幕中央的非侵入式提示：
#   - 区域名称进入提示（大字渐显 → 渐隐）
#   - Boss 出现提示（震动 + 红色大字）
#   - 新物品拾取队列（右下角堆叠）
#   - 通用通知（操作成功/失败等）
#
# 核心类：
#   Notification        — 单条通知
#   NotificationManager — 通知管理器
# =============================================================
from __future__ import annotations
from typing import Optional, List, Tuple

import pygame

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from config import SCREEN_WIDTH, SCREEN_HEIGHT


# ---- 通知类型预设 ----
NOTIFICATION_TYPES = {
    "area_name": {
        "font_size": 48,
        "color":     (255, 230, 170),
        "duration":  3.0,
        "fade_in":   1.0,
        "fade_out":  1.5,
        "pos":       "center",
    },
    "boss_appear": {
        "font_size": 44,
        "color":     (220, 50, 50),
        "duration":  3.5,
        "fade_in":   0.6,
        "fade_out":  2.0,
        "pos":       "center",
        "shake":     True,
    },
    "item_pickup": {
        "font_size": 16,
        "color":     (200, 230, 160),
        "duration":  2.0,
        "fade_in":   0.2,
        "fade_out":  1.5,
        "pos":       "bottom_right",
    },
    "souls": {
        "font_size": 20,
        "color":     (180, 255, 140),
        "duration":  2.0,
        "fade_in":   0.2,
        "fade_out":  1.5,
        "pos":       "bottom_right",
    },
    "info": {
        "font_size": 22,
        "color":     (200, 200, 220),
        "duration":  2.5,
        "fade_in":   0.5,
        "fade_out":  1.5,
        "pos":       "center",
    },
    "warning": {
        "font_size": 24,
        "color":     (255, 150, 60),
        "duration":  2.5,
        "fade_in":   0.3,
        "fade_out":  1.5,
        "pos":       "center",
    },
}


class Notification:
    """单条通知"""

    __slots__ = (
        "text", "color", "font_size", "duration", "fade_in",
        "fade_out", "elapsed", "active", "pos_type", "shake",
        "_start_y",
    )

    def __init__(self,
                 text: str,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 font_size: int = 24,
                 duration: float = 2.5,
                 fade_in: float = 0.5,
                 fade_out: float = 1.5,
                 pos_type: str = "center",
                 shake: bool = False):
        self.text      = text
        self.color     = color
        self.font_size = font_size
        self.duration  = duration
        self.fade_in   = fade_in
        self.fade_out  = fade_out
        self.elapsed   = 0.0
        self.active    = True
        self.pos_type  = pos_type
        self.shake     = shake
        self._start_y  = SCREEN_HEIGHT // 2 - 50   # 记录起始 Y（震动用）

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / max(self.duration, 0.001))

    @property
    def alpha(self) -> int:
        """当前透明度 0~255"""
        dur = max(self.fade_in + self.fade_out, 0.001)
        t = self.elapsed
        # 渐入
        if t < self.fade_in:
            return int(255 * t / self.fade_in)
        # 保持
        stay_start = self.fade_in
        stay_end   = self.duration - self.fade_out
        if t < stay_end:
            return 255
        # 渐出
        fade_section = self.duration - stay_end
        if fade_section > 0:
            return int(255 * (1.0 - (t - stay_end) / fade_section))
        return 0

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False
        return self.active

    def get_position(self) -> Tuple[int, int]:
        """获取绘制位置"""
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        margin = 20

        if self.pos_type == "center":
            y = cy - 50
        elif self.pos_type == "bottom_right":
            x = SCREEN_WIDTH - margin
            y = SCREEN_HEIGHT - margin
            return x, y
        elif self.pos_type == "center_top":
            y = cy - 200
        else:
            y = cy

        # 震动效果（Boss 出现）
        if self.shake and self.elapsed < 1.5:
            import random
            shake_amount = max(0, 6 * (1.0 - self.elapsed / 1.5))
            cx += int(random.uniform(-shake_amount, shake_amount))
            y  += int(random.uniform(-shake_amount, shake_amount))

        return cx, y


class NotificationManager(BaseWidget):
    """
    通知管理器。

    用法：
        nm = NotificationManager()

        # 区域名称
        nm.show_area("古墓地带")

        # Boss 出现
        nm.show_boss("腐骨公爵 降临")

        # 物品拾取
        nm.show_item_pickup("草药汤 ×3")

        # 通用
        nm.show("传送成功", type="info")
    """

    # 右下角堆叠最大条目数
    MAX_STACK_ITEMS = 5

    def __init__(self):
        super().__init__(visible=True, z_index=60)
        self._notifications: List[Notification] = []
        self._stack_items: List[Notification] = []   # 右下角堆叠

    # ----------------------------------------------------------------
    # 快捷方法
    # ----------------------------------------------------------------

    def show_area(self, name: str) -> None:
        """显示区域名称提示"""
        cfg = NOTIFICATION_TYPES["area_name"]
        self._notifications.append(
            Notification(name, cfg["color"], cfg["font_size"],
                         cfg["duration"], cfg["fade_in"], cfg["fade_out"],
                         cfg["pos"])
        )

    def show_boss(self, name: str) -> None:
        """显示 Boss 出现提示"""
        cfg = NOTIFICATION_TYPES["boss_appear"]
        self._notifications.append(
            Notification(name, cfg["color"], cfg["font_size"],
                         cfg["duration"], cfg["fade_in"], cfg["fade_out"],
                         cfg["pos"], cfg.get("shake", False))
        )

    def show_item_pickup(self, text: str) -> None:
        """显示物品拾取提示（右下角堆叠）"""
        cfg = NOTIFICATION_TYPES["item_pickup"]
        notif = Notification(text, cfg["color"], cfg["font_size"],
                            cfg["duration"], cfg["fade_in"], cfg["fade_out"],
                            cfg["pos"])
        self._stack_items.append(notif)
        # 保持最多 MAX_STACK_ITEMS 条
        if len(self._stack_items) > self.MAX_STACK_ITEMS:
            # 删除最老的
            oldest = self._stack_items.pop(0)
            oldest.active = False

    def show_souls(self, text: str) -> None:
        """显示灵魂获取提示"""
        cfg = NOTIFICATION_TYPES["souls"]
        self._stack_items.append(
            Notification(text, cfg["color"], cfg["font_size"],
                        cfg["duration"], cfg["fade_in"], cfg["fade_out"],
                        cfg["pos"])
        )

    def show(self, text: str, ntype: str = "info") -> None:
        """通用通知"""
        cfg = NOTIFICATION_TYPES.get(ntype, NOTIFICATION_TYPES["info"])
        self._notifications.append(
            Notification(text, cfg["color"], cfg["font_size"],
                         cfg["duration"], cfg["fade_in"], cfg["fade_out"],
                         cfg["pos"])
        )

    # ----------------------------------------------------------------
    # 每帧接口
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        # 中央通知
        alive = []
        for n in self._notifications:
            if n.update(dt):
                alive.append(n)
        self._notifications = alive

        # 右下角堆叠
        stack_alive = []
        for n in self._stack_items:
            if n.update(dt):
                stack_alive.append(n)
        self._stack_items = stack_alive

    def render(self, surface: pygame.Surface) -> None:
        """绘制所有活跃通知"""
        if not self.visible:
            return

        # 中央通知（大字）
        for n in self._notifications:
            self._render_single(surface, n)

        # 右下角堆叠
        margin = 20
        base_y = SCREEN_HEIGHT - margin
        # 从底部往上堆叠
        for i, n in enumerate(reversed(self._stack_items)):
            self._render_stacked(surface, n, index=i, base_y=base_y, margin=margin)

    def _render_single(self, surface: pygame.Surface, n: Notification) -> None:
        alpha = n.alpha
        if alpha <= 0:
            return

        font = get_font(n.font_size, bold=True)
        text_surf = font.render(n.text, True, n.color)

        # alpha
        if alpha < 255:
            text_surf.set_alpha(alpha)

        x, y = n.get_position()

        # 中央通知以文字中心对齐
        if n.pos_type != "bottom_right":
            x -= text_surf.get_width() // 2
            y -= text_surf.get_height() // 2

        surface.blit(text_surf, (x, y))

    def _render_stacked(self, surface: pygame.Surface, n: Notification,
                        index: int, base_y: int, margin: int) -> None:
        alpha = n.alpha
        if alpha <= 0:
            return

        font = get_font(n.font_size)
        text_surf = font.render(n.text, True, n.color)

        if alpha < 255:
            text_surf.set_alpha(alpha)

        # 右下角：右对齐，从底部往上堆叠
        x = SCREEN_WIDTH - margin - text_surf.get_width()
        y = base_y - (index + 1) * 24

        surface.blit(text_surf, (x, y))

    def clear(self) -> None:
        """清除所有通知"""
        self._notifications.clear()
        self._stack_items.clear()
