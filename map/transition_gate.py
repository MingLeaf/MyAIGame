# =============================================================
# map/transition_gate.py —— 区域传送门 / 入口
# =============================================================

from __future__ import annotations
import pygame

from utils.color import UI_HIGHLIGHT
from ui.font_manager import get_font


class TransitionGate:
    """
    区域传送触发器。
    当玩家矩形与触发区域重叠时，通知场景系统切换区域。
    """

    def __init__(self,
                 rect: pygame.Rect,
                 target_area: str,
                 target_spawn: str = "default",
                 direction: str = "right"):
        """
        :param rect:          触发区域（世界坐标）
        :param target_area:   目标区域 ID（对应 world_config.json 中的 area id）
        :param target_spawn:  目标区域的出生点标签
        :param direction:     传送方向提示（left/right/up/down）
        """
        self.rect         = rect
        self.target_area  = target_area
        self.target_spawn = target_spawn
        self.direction    = direction
        self.enabled      = True
        self._triggered   = False

    def check(self, entity_rect: pygame.Rect) -> bool:
        """
        检测实体是否触碰传送门。
        返回 True 表示触发传送（每次进入只触发一次，离开后重置）。
        """
        if not self.enabled:
            return False
        if self.rect.colliderect(entity_rect):
            if not self._triggered:
                self._triggered = True
                return True
        else:
            self._triggered = False
        return False

    def render_debug(self, surface: pygame.Surface, cam_offset: tuple):
        draw_rect = self.rect.move(-cam_offset[0], -cam_offset[1])
        pygame.draw.rect(surface, UI_HIGHLIGHT, draw_rect, 2)
        font = get_font(18)
        label = font.render(f"→ {self.target_area}", True, UI_HIGHLIGHT)
        surface.blit(label, draw_rect.topleft)
