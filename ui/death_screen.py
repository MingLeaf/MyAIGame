# =============================================================
# ui/death_screen.py —— 死亡界面（"YOU DIED" + 复活按钮）
#
# 第 8.1 阶段：玩家死亡后显示全屏死亡界面，
# 提示灵魂碎片遗失位置，按 F 从最近营地复活。
# =============================================================
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

from utils.color import WHITE, UI_HIGHLIGHT
from ui.font_manager import get_font
from config import SCREEN_WIDTH, SCREEN_HEIGHT

if TYPE_CHECKING:
    from entities.player.player import Player


class DeathScreen:
    """
    全屏死亡界面。
    - 黑底渐显
    - "YOU DIED" 大标题
    - 灵魂碎片遗失数量提示
    - 按 E 从最近营地复活
    - 按 ESC 回到主菜单
    """

    # 渐显时间
    FADE_DURATION = 1.0
    # 复活前最小等待（防止误操作）
    MIN_DELAY = 0.8

    def __init__(self):
        self.visible: bool = False
        self._fade_timer: float = 0.0
        self._delay_timer: float = 0.0
        self._lost_souls: int = 0
        self._death_x: float = 0
        self._death_y: float = 0
        self._can_respawn: bool = False

    def show(self, lost_souls: int, death_x: float = 0, death_y: float = 0) -> None:
        """显示死亡界面。"""
        self.visible = True
        self._fade_timer = 0.0
        self._delay_timer = 0.0
        self._lost_souls = lost_souls
        self._death_x = death_x
        self._death_y = death_y
        self._can_respawn = False

    def hide(self) -> None:
        """隐藏死亡界面。"""
        self.visible = False

    def update(self, dt: float) -> None:
        if not self.visible:
            return
        self._fade_timer = min(self._fade_timer + dt, self.FADE_DURATION)
        self._delay_timer += dt
        if self._delay_timer >= self.MIN_DELAY:
            self._can_respawn = True

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        处理输入事件。
        :return: "respawn" 表示请求复活, "quit" 表示退出到主菜单, None 表示无操作
        """
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e and self._can_respawn:
                return "respawn"
            if event.key == pygame.K_ESCAPE:
                return "quit"
        return None

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        # 黑底渐显
        alpha = min(1.0, self._fade_timer / self.FADE_DURATION)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(200 * alpha)))
        surface.blit(overlay, (0, 0))

        if alpha < 0.4:
            return   # 渐显初期不显示文字

        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2

        # "YOU DIED" 大标题（红色）
        title_font = get_font(56)
        title_surf = title_font.render("你 已 陨 落", True, (200, 30, 30))
        title_rect = title_surf.get_rect(center=(center_x, center_y - 100))
        # 红色描边
        outline = title_font.render("你 已 陨 落", True, (80, 10, 10))
        surface.blit(outline, title_rect.move(2, 2))
        surface.blit(title_surf, title_rect)

        # 英文小字
        sub_font = get_font(20)
        sub_surf = sub_font.render("YOU DIED", True, (160, 60, 60))
        sub_rect = sub_surf.get_rect(center=(center_x, center_y - 50))
        surface.blit(sub_surf, sub_rect)

        # 灵魂碎片遗失提示
        info_font = get_font(22)
        if self._lost_souls > 0:
            info_text = f"◇ 遗失了 {self._lost_souls} 灵魂碎片"
            info_color = (255, 200, 100)
        else:
            info_text = "你没有灵魂碎片可遗失"
            info_color = (140, 140, 160)

        info_surf = info_font.render(info_text, True, info_color)
        info_rect = info_surf.get_rect(center=(center_x, center_y + 20))
        surface.blit(info_surf, info_rect)

        # 遗物位置提示
        if self._lost_souls > 0:
            pos_font = get_font(16)
            pos_text = f"遗物留在击杀点附近 — 回到该处捡回"
            pos_surf = pos_font.render(pos_text, True, (160, 160, 180))
            pos_rect = pos_surf.get_rect(center=(center_x, center_y + 50))
            surface.blit(pos_surf, pos_rect)

        # 操作提示（闪烁效果）
        if self._can_respawn:
            blink = int(pygame.time.get_ticks() * 0.003) % 2
            hint_font = get_font(26)
            hint_text = "按 [E] 从最近营地复活"
            if blink:
                hint_surf = hint_font.render(hint_text, True, UI_HIGHLIGHT)
            else:
                hint_surf = hint_font.render(hint_text, True, (180, 200, 255))
            hint_rect = hint_surf.get_rect(center=(center_x, center_y + 130))
            surface.blit(hint_surf, hint_rect)

        # 退出提示
        esc_font = get_font(16)
        esc_surf = esc_font.render("按 [ESC] 回到主菜单", True, (120, 120, 140))
        esc_rect = esc_surf.get_rect(center=(center_x, center_y + 170))
        surface.blit(esc_surf, esc_rect)
