# =============================================================
# ui/settings_ui.py —— 设置界面
#
# 功能：
#   - 音量滑块（主音量 / BGM / SFX）
#   - 键位重映射（点击 → 按新键 → input_handler.remap）
#   - 分辨率切换（全屏/窗口）
#   - 应用 / 取消 / 恢复默认
#
# 操作：
#   W/S/↑↓ 选择设置项
#   A/D/←→ 调整滑块值（音量/分辨率）
#   Enter 开始键位重映射
#   按任意新键 → 更新键位
#   ESC 取消 / 返回
# =============================================================
from __future__ import annotations
from typing import Optional, Dict, List, Tuple

import pygame

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from utils.color import UI_BG, UI_TEXT, UI_HIGHLIGHT
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from core.input_handler import DEFAULT_KEY_MAP, input_handler


# ---- 设置项类型 ----
SETTING_SLIDER      = "slider"
SETTING_KEYBIND     = "keybind"
SETTING_TOGGLE      = "toggle"
SETTING_SECTION     = "section"

# 动作名中文映射
ACTION_DISPLAY_NAMES = {
    "move_left":    "向左移动",
    "move_right":   "向右移动",
    "move_up":      "向上移动",
    "move_down":    "向下移动",
    "attack_light": "轻攻击",
    "attack_heavy": "重攻击",
    "roll":         "翻滚",
    "block":        "格挡",
    "weapon_art":   "战技",
    "interact":     "交互",
    "use_item":     "使用物品",
    "pause":        "暂停",
    "inventory":    "背包",
    "jump":         "跳跃",
    "debug_toggle": "调试",
}

# pygame keycode → 显示名
_KEY_DISPLAY = {
    pygame.K_a: "A", pygame.K_b: "B", pygame.K_c: "C", pygame.K_d: "D",
    pygame.K_e: "E", pygame.K_f: "F", pygame.K_g: "G", pygame.K_h: "H",
    pygame.K_i: "I", pygame.K_j: "J", pygame.K_k: "K", pygame.K_l: "L",
    pygame.K_m: "M", pygame.K_n: "N", pygame.K_o: "O", pygame.K_p: "P",
    pygame.K_q: "Q", pygame.K_r: "R", pygame.K_s: "S", pygame.K_t: "T",
    pygame.K_u: "U", pygame.K_v: "V", pygame.K_w: "W", pygame.K_x: "X",
    pygame.K_y: "Y", pygame.K_z: "Z",
    pygame.K_SPACE: "Space",
    pygame.K_LSHIFT: "LShift", pygame.K_RSHIFT: "RShift",
    pygame.K_LCTRL: "LCtrl", pygame.K_RCTRL: "RCtrl",
    pygame.K_ESCAPE: "Esc", pygame.K_RETURN: "Enter",
    pygame.K_TAB: "Tab", pygame.K_BACKSPACE: "Back",
    pygame.K_F1: "F1", pygame.K_F2: "F2", pygame.K_F3: "F3",
    pygame.K_F4: "F4", pygame.K_F5: "F5", pygame.K_F6: "F6",
    pygame.K_F7: "F7", pygame.K_F8: "F8", pygame.K_F9: "F9",
    pygame.K_F10: "F10", pygame.K_F11: "F11", pygame.K_F12: "F12",
}

# 分辨率预设
_RESOLUTIONS = [
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
]


def _keycode_name(code: int) -> str:
    return _KEY_DISPLAY.get(code, f"Key({code})")


class SettingsUI(BaseWidget):
    """
    设置界面。

    用法：
        settings = SettingsUI()
        settings.open()

        # handle_events
        action = settings.handle_event(event)  # "apply" / "cancel" / None -> 持续

        # render (最后调用)
        settings.render(surface)
    """

    def __init__(self):
        super().__init__(visible=False, z_index=60)

        # ---- 设置项列表 ----
        self._items: List[Dict] = []

        # 音量
        self._master_volume = 0.8
        self._bgm_volume    = 0.7
        self._sfx_volume    = 0.9

        # 分辨率索引
        self._resolution_idx = 0

        # 全屏
        self._fullscreen = False

        # 当前键位（从 input_handler 拷贝）
        self._key_map: Dict[str, int] = {}

        # 选中索引
        self._selected: int = 0

        # 键位重映射状态
        self._remapping_action: Optional[str] = None  # 正在等待按键
        self._remap_flash: float = 0.0

        # 消息
        self._message: str = ""
        self._msg_timer: float = 0.0

        self._build_items()

    # ----------------------------------------------------------------
    # 构建设置项列表
    # ----------------------------------------------------------------

    def _build_items(self):
        """构建平铺的设置项列表"""
        self._items = [
            # 音量
            {"type": SETTING_SECTION, "label": "音  量"},
            {"type": SETTING_SLIDER,  "label": "主音量", "value": self._master_volume, "attr": "_master_volume"},
            {"type": SETTING_SLIDER,  "label": "背景音乐", "value": self._bgm_volume, "attr": "_bgm_volume"},
            {"type": SETTING_SLIDER,  "label": "音效", "value": self._sfx_volume, "attr": "_sfx_volume"},

            # 画面
            {"type": SETTING_SECTION, "label": "画  面"},
            {"type": SETTING_TOGGLE,  "label": "全屏", "value": self._fullscreen, "attr": "_fullscreen"},
        ]

        # 分辨率
        for i, (w, h) in enumerate(_RESOLUTIONS):
            self._items.append({
                "type": SETTING_TOGGLE,
                "label": f"{w}×{h}",
                "value": (i == self._resolution_idx),
                "res_idx": i,
            })

        # 键位
        self._items.append({"type": SETTING_SECTION, "label": "键位设置"})

        self._key_map = dict(input_handler._key_map)
        for action, keycode in self._key_map.items():
            display = ACTION_DISPLAY_NAMES.get(action, action)
            self._items.append({
                "type": SETTING_KEYBIND,
                "label": display,
                "action": action,
                "keycode": keycode,
            })

    # ----------------------------------------------------------------
    # 开关
    # ----------------------------------------------------------------

    def open(self) -> None:
        self.visible = True
        self._selected = 0
        self._remapping_action = None
        self._message = ""
        self._build_items()

    def close(self) -> None:
        self.visible = False
        self._remapping_action = None

    # ----------------------------------------------------------------
    # 事件
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        返回 "apply" (应用) / "cancel" (取消) / None (持续显示)
        """
        if not self.visible:
            return None

        # 键位重映射中
        if self._remapping_action is not None:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._remapping_action = None
                else:
                    self._key_map[self._remapping_action] = event.key
                    self._remapping_action = None
                    self._sync_keybind_items()
            return None

        if event.type != pygame.KEYDOWN:
            return None

        # 上下导航
        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected = max(0, self._selected - 1)
            # 跳过 section 和不可选项
            while self._items[self._selected]["type"] == SETTING_SECTION:
                self._selected = max(0, self._selected - 1)
            return None

        if event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected = min(len(self._items) - 1, self._selected + 1)
            while self._items[self._selected]["type"] == SETTING_SECTION:
                self._selected = min(len(self._items) - 1, self._selected + 1)
            return None

        if event.key == pygame.K_ESCAPE:
            return "cancel"

        item = self._items[self._selected]

        # 滑块：左/右调整
        if item["type"] == SETTING_SLIDER:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                val = max(0.0, self._get_item_value(item) - 0.05)
                self._set_item_value(item, round(val, 2))
                self._refresh_item(item)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                val = min(1.0, self._get_item_value(item) + 0.05)
                self._set_item_value(item, round(val, 2))
                self._refresh_item(item)

        # 键位
        elif item["type"] == SETTING_KEYBIND:
            if event.key == pygame.K_RETURN:
                self._remapping_action = item["action"]
            elif event.key == pygame.K_BACKSPACE:
                # 恢复默认
                default = DEFAULT_KEY_MAP.get(item["action"])
                if default is not None:
                    self._key_map[item["action"]] = default
                    self._sync_keybind_items()

        # 开关
        elif item["type"] == SETTING_TOGGLE:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if "res_idx" in item:
                    # 分辨率选择
                    self._resolution_idx = item["res_idx"]
                    self._refresh_resolution_items()
                else:
                    # 其他 toggle
                    new_val = not self._get_item_value(item)
                    self._set_item_value(item, new_val)
                    self._refresh_item(item)

        return None

    def _get_item_value(self, item: Dict):
        """从实例属性读取值"""
        attr = item.get("attr")
        if attr and hasattr(self, attr):
            return getattr(self, attr)
        return item.get("value", 0)

    def _set_item_value(self, item: Dict, value):
        attr = item.get("attr")
        if attr and hasattr(self, attr):
            setattr(self, attr, value)
        item["value"] = value

    def _refresh_item(self, item: Dict):
        item["value"] = self._get_item_value(item)

    def _sync_keybind_items(self):
        """同步键位映射到 UI"""
        for item in self._items:
            if item["type"] == SETTING_KEYBIND:
                item["keycode"] = self._key_map.get(item["action"], 0)

    def _refresh_resolution_items(self):
        """同步分辨率选中状态"""
        for item in self._items:
            if "res_idx" in item:
                item["value"] = (item["res_idx"] == self._resolution_idx)

    # ----------------------------------------------------------------
    # 应用设置
    # ----------------------------------------------------------------

    def apply_settings(self):
        """将设置写入实际系统"""
        # 音量
        try:
            pygame.mixer.music.set_volume(self._master_volume * self._bgm_volume)
            # SFX 音量后续通过 AudioManager 同步
        except Exception:
            pass

        # 键位
        for action, keycode in self._key_map.items():
            input_handler.remap(action, keycode)

    # ----------------------------------------------------------------
    # 更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self._remap_flash > 0:
            self._remap_flash = max(0, self._remap_flash - dt)
        if self._msg_timer > 0:
            self._msg_timer = max(0, self._msg_timer - dt)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        # 背景
        surface.fill(UI_BG)

        cx = SCREEN_WIDTH // 2

        # 标题
        title_font = get_font(40, bold=True)
        title_surf = title_font.render("设  置", True, UI_HIGHLIGHT)
        surface.blit(title_surf, title_surf.get_rect(center=(cx, 40)))

        # 滚动偏移（使选中项在可见范围内）
        visible_start = max(0, self._selected - 8)
        scroll_y = 90
        line_h = 40

        item_font = get_font(22)
        value_font = get_font(20)

        for i, item in enumerate(self._items[visible_start:]):
            idx = visible_start + i
            y = scroll_y + i * line_h

            if y > SCREEN_HEIGHT - 60:
                break

            is_sel = (idx == self._selected)
            item_type = item["type"]

            # 高亮行背景
            if is_sel and item_type != SETTING_SECTION:
                pygame.draw.rect(surface, (45, 40, 62),
                                (cx - 380, y - 2, 760, line_h - 2),
                                border_radius=4)

            if item_type == SETTING_SECTION:
                # 分区标题
                sec_font = get_font(26, bold=True)
                sec_surf = sec_font.render(item["label"], True, (180, 160, 100))
                surface.blit(sec_surf, (cx - 380, y))
                # 分隔线
                pygame.draw.line(surface, (60, 55, 80),
                                (cx - 380, y + 34), (cx + 380, y + 34), 1)
                continue

            # 标签
            color = UI_HIGHLIGHT if is_sel else UI_TEXT
            lbl_surf = item_font.render(item["label"], True, color)
            surface.blit(lbl_surf, (cx - 360, y + 6))

            # 值区
            val_x = cx + 80

            if item_type == SETTING_SLIDER:
                self._render_slider(surface, val_x, y + 6, item, is_sel)

            elif item_type == SETTING_KEYBIND:
                self._render_keybind(surface, val_x, y + 6, item, is_sel)

            elif item_type == SETTING_TOGGLE:
                self._render_toggle(surface, val_x, y + 6, item, is_sel)

        # 底部提示
        hint_font = get_font(16)
        hints_y = SCREEN_HEIGHT - 50

        if self._remapping_action is not None:
            action_display = ACTION_DISPLAY_NAMES.get(
                self._remapping_action, self._remapping_action)
            hint_surf = hint_font.render(
                f"请按下「{action_display}」的新按键……（ESC 取消）",
                True, (255, 200, 80))
        else:
            hint_surf = hint_font.render(
                "↑↓ 导航    Enter/Space 修改    ESC 返回",
                True, (120, 120, 140))

        surface.blit(hint_surf, hint_surf.get_rect(center=(cx, hints_y)))

        # 应用按钮提示
        apply_font = get_font(18)
        apply_surf = apply_font.render(
            "设置即时生效（键位在关闭后生效）", True, (140, 140, 160))
        surface.blit(apply_surf, apply_surf.get_rect(center=(cx, hints_y + 26)))

    def _render_slider(self, surface, x, y, item, is_sel):
        """渲染滑块"""
        val = self._get_item_value(item)
        bar_w = 200
        bar_h = 14

        # 背景
        pygame.draw.rect(surface, (40, 38, 55),
                        (x, y + 4, bar_w, bar_h), border_radius=7)
        # 填充
        fill_w = int(bar_w * val)
        if fill_w > 0:
            color = (120, 180, 240) if is_sel else (80, 130, 190)
            pygame.draw.rect(surface, color,
                            (x, y + 4, fill_w, bar_h), border_radius=7)
        # 边框
        border_c = (180, 170, 210) if is_sel else (90, 85, 110)
        pygame.draw.rect(surface, border_c,
                        (x, y + 4, bar_w, bar_h), 1, border_radius=7)

        # 数值
        pct_font = get_font(16)
        pct = pct_font.render(f"{int(val * 100)}%", True, UI_TEXT)
        surface.blit(pct, (x + bar_w + 10, y + 2))

    def _render_keybind(self, surface, x, y, item, is_sel):
        """渲染键位显示"""
        keycode = item["keycode"]
        key_name = _keycode_name(keycode)

        if is_sel and self._remapping_action == item["action"]:
            color = UI_HIGHLIGHT
            text = "…"
        else:
            color = UI_HIGHLIGHT if is_sel else (180, 200, 220)
            text = key_name

        key_font = get_font(20)
        key_surf = key_font.render(text, True, color)
        surface.blit(key_surf, (x, y + 4))

        # 操作提示
        if is_sel and self._remapping_action is None:
            hint = get_font(14).render("Enter修改  Backspace恢复", True,
                                       (130, 130, 155))
            surface.blit(hint, (x + 120, y + 7))

    def _render_toggle(self, surface, x, y, item, is_sel):
        """渲染开关/选择项"""
        val = self._get_item_value(item)
        color = UI_HIGHLIGHT if val else (140, 140, 160)
        text = "● 开" if val else "○ 关"

        # 分辨率特殊处理
        if "res_idx" in item:
            text = "●" if val else "○"

        toggle_font = get_font(20)
        tog_surf = toggle_font.render(text, True, color)
        surface.blit(tog_surf, (x, y + 4))
