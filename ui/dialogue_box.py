# =============================================================
# ui/dialogue_box.py —— NPC 对话框 UI（底部半透明面板 / 逐字显示 / 选项）
# 第 10 阶段：NPC 与对话系统
# =============================================================

from __future__ import annotations
import pygame, logging
from typing import Optional, List, Dict, Any, Callable

from utils.color import WHITE, UI_HIGHLIGHT
from ui.font_manager import get_font
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from core.dialogue_engine import DialogueEngine

_log = logging.getLogger("dialogue")


class DialogueBox:
    """
    NPC 对话框覆盖层。
    底部半透明黑底，NPC 名称 + 逐字显示文本 + 选项列表。
    W/S 选择选项，Enter 确认，ESC 关闭。
    """

    # 逐字显示速度（字符/秒）
    TEXT_SPEED = 40.0

    def __init__(self):
        self.visible: bool = False
        self._engine: Optional[DialogueEngine] = None
        self._speaker_name: str = ""
        self._full_text: str = ""
        self._revealed_chars: int = 0
        self._reveal_timer: float = 0.0
        self._text_done: bool = False
        self._selected_choice: int = 0

        # 面板尺寸
        self._box_h = 180
        self._box_y = SCREEN_HEIGHT - self._box_h - 20

        # 消息提示（动作结果反馈）
        self._message: str = ""
        self._msg_timer: float = 0.0

    # ---- 打开/关闭 ----

    def open(self, engine: DialogueEngine, speaker_name: str = ""):
        self.visible = True
        self._engine = engine
        self._speaker_name = speaker_name
        self._start_text(engine.current_text)
        self._selected_choice = 0
        self._message = ""
        self._msg_timer = 0.0
        _log.info("OPEN speaker=%s text=%s", speaker_name, engine.current_text[:40])

    def close(self):
        _log.info("CLOSE speaker=%s", self._speaker_name)
        self.visible = False
        if self._engine:
            self._engine.close()
        self._engine = None
        from core.event_manager import event_manager
        event_manager.emit("dialogue_closed", {})

    def is_open(self) -> bool:
        return self.visible

    # ---- 逐字显示 ----

    def _start_text(self, text: str):
        self._full_text = text
        self._revealed_chars = 0
        self._reveal_timer = 0.0
        self._text_done = (len(text) == 0)

    # ---- 事件处理 ----

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理键盘事件。返回 True 表示已消耗。"""
        if not self.visible or self._engine is None:
            return False

        if event.type != pygame.KEYDOWN:
            return True

        # 文本尚未完全显示 → 按 Enter/Space 快进
        if not self._text_done:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._revealed_chars = len(self._full_text)
                self._text_done = True
            elif event.key == pygame.K_ESCAPE:
                self.close()
            return True

        # 文本已显示完 → 处理选项
        choices = self._engine.current_choices
        if not choices:
            # 无选项 → 任意键关闭
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_f):
                self.close()
            return True

        if event.key in (pygame.K_w, pygame.K_UP):
            self._selected_choice = (self._selected_choice - 1) % len(choices)
            return True
        if event.key in (pygame.K_s, pygame.K_DOWN):
            self._selected_choice = (self._selected_choice + 1) % len(choices)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            action = self._engine.select_choice(self._selected_choice)
            _log.info("SELECT choice=%d action=%s engine_alive=%s",
                      self._selected_choice, action, self._engine is not None)
            # 动作回调可能已通过事件系统关闭对话，需检查 engine 仍存在
            if self._engine is None:
                return True
            if self._engine.is_active:
                # 还有下一段对话
                self._start_text(self._engine.current_text)
                self._selected_choice = 0
            else:
                # 对话结束
                self.close()
            if action:
                self._message = f"已执行: {action}"
                self._msg_timer = 1.5
            return True
        if event.key == pygame.K_ESCAPE:
            self.close()
            return True

        return True

    # ---- 更新 ----

    def update(self, dt: float):
        if not self.visible or self._engine is None:
            return

        # 逐字显示
        if not self._text_done:
            self._reveal_timer += dt
            chars_per_frame = self.TEXT_SPEED * dt
            if chars_per_frame >= 1:
                self._revealed_chars = min(
                    len(self._full_text),
                    self._revealed_chars + max(1, int(chars_per_frame))
                )
            if self._revealed_chars >= len(self._full_text):
                self._text_done = True

        # 消息计时器
        if self._msg_timer > 0:
            self._msg_timer = max(0, self._msg_timer - dt)

    # ---- 渲染 ----

    def render(self, surface: pygame.Surface):
        if not self.visible or self._engine is None:
            return

        # 半透明遮罩（轻度，不完全遮挡游戏画面）
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 60))
        surface.blit(overlay, (0, 0))

        # 底部对话框
        bx, bw = 40, SCREEN_WIDTH - 80
        by = self._box_y
        bh = self._box_h

        # 背景面板
        panel = pygame.Surface((bw, bh), pygame.SRCALPHA)
        panel.fill((10, 8, 20, 220))
        pygame.draw.rect(panel, (80, 75, 100), (0, 0, bw, bh), 2)
        surface.blit(panel, (bx, by))

        # NPC 名称
        name_font = get_font(20)
        name_surf = name_font.render(self._speaker_name, True, UI_HIGHLIGHT)
        surface.blit(name_surf, (bx + 16, by + 10))

        # 对话文本（逐字显示）
        text_font = get_font(18)
        revealed = self._full_text[:self._revealed_chars]
        # 文字换行
        lines = self._wrap_text(revealed, text_font, bw - 32)
        for i, line in enumerate(lines):
            if i >= 3:  # 最多 3 行
                break
            line_surf = text_font.render(line, True, (220, 220, 230))
            surface.blit(line_surf, (bx + 16, by + 36 + i * 22))

        # 继续提示（文本显示完毕后，有选项则等待选择）
        if self._text_done and self._engine and self._engine.current_choices:
            # 渲染选项
            choices = self._engine.current_choices
            opt_font = get_font(18)
            opt_start_y = by + bh - 14 - len(choices) * 26
            for i, choice in enumerate(choices):
                y = opt_start_y + i * 26
                if i == self._selected_choice:
                    prefix = "▶ "
                    color = UI_HIGHLIGHT
                else:
                    prefix = "   "
                    color = (160, 160, 180)
                opt_surf = opt_font.render(f"{prefix}{choice.get('text', '')}", True, color)
                surface.blit(opt_surf, (bx + 24, y))

        # 操作提示
        hint_font = get_font(14)
        if self._text_done:
            if self._engine and self._engine.current_choices:
                hint = "W/S: 选择  Enter: 确认  ESC: 关闭"
            else:
                hint = "Enter/Space: 继续  ESC: 关闭"
            hint_surf = hint_font.render(hint, True, (130, 130, 150))
            surface.blit(hint_surf, (bx + bw - hint_surf.get_width() - 16, by + bh - 18))

        # 消息提示
        if self._message and self._msg_timer > 0:
            msg_font = get_font(16)
            msg_surf = msg_font.render(self._message, True, (200, 200, 120))
            surface.blit(msg_surf, (bx + 16, by + bh + 4))

    @staticmethod
    def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list:
        """简单换行：按字符数估算，中文约 2x 英文字符宽度。"""
        if not text:
            return [""]
        # 粗略估计每行最多字符数
        char_width = font.size("测")[0]  # 中文字符宽度
        if char_width == 0:
            char_width = font.size("A")[0] * 2
        max_chars = max(1, max_width // char_width)

        lines = []
        i = 0
        while i < len(text):
            lines.append(text[i:i + max_chars])
            i += max_chars
        return lines
