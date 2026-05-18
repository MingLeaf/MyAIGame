# =============================================================
# ui/status_panel.py —— 人物属性面板
#
# 按 Tab 键打开，覆盖在游戏画面之上。
# 展示：
#   - 六项成长属性（力量/敏捷/智慧/信仰/体魄/耐性）+ 分配点数
#   - 战斗属性衍生（HP/Stamina/Mana/ATK/DEF/负载/翻滚类型）
#   - 装备概览（当前武器+护甲）
#   - 状态异常显示
#
# 操作：
#   1~6 键：分配属性点（若 unspent > 0）
#   Tab / ESC：关闭面板
# =============================================================
from __future__ import annotations
from typing import Optional, Dict, TYPE_CHECKING

import pygame

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from config import SCREEN_WIDTH, SCREEN_HEIGHT

if TYPE_CHECKING:
    from entities.player.player import Player


# ---- 属性名称与描述 ----
ATTR_KEYS = ["strength", "dexterity", "intelligence", "faith", "vitality", "endurance"]

ATTR_DISPLAY = {
    "strength":     ("力量", "重型武器伤害↑，满足重武器装备", (220, 120, 80)),
    "dexterity":    ("敏捷", "轻型武器伤害↑，翻滚距离↑",      (80, 200, 120)),
    "intelligence": ("智慧", "魔法伤害↑，法术消耗品效果↑",    (100, 140, 240)),
    "faith":        ("信仰", "神圣伤害↑，治疗消耗品效果↑",    (220, 200, 100)),
    "vitality":     ("体魄", "最大HP↑，耐力恢复速度↑",        (220, 80, 80)),
    "endurance":    ("耐性", "最大耐力↑，最大负重↑",           (140, 200, 100)),
}

ROLL_NAMES = {
    "fast":   ("快速翻滚", (100, 220, 150)),
    "normal": ("普通翻滚", (200, 200, 100)),
    "slow":   ("慢速翻滚", (220, 150, 80)),
    "unable": ("无法翻滚", (220, 80, 80)),
}


class StatusPanel(BaseWidget):
    """
    人物属性面板覆盖层。
    """

    def __init__(self):
        super().__init__(visible=False, z_index=55)
        self.is_open: bool = False
        self._player: Optional["Player"] = None
        self._selected_attr: int = 0

    # ----------------------------------------------------------------
    # 开关
    # ----------------------------------------------------------------

    def toggle(self, player: "Player"):
        self.is_open = not self.is_open
        self.visible = self.is_open
        if self.is_open:
            self._player = player
            self._selected_attr = 0

    def open(self, player: "Player"):
        self.is_open = True
        self.visible = True
        self._player = player
        self._selected_attr = 0

    def close(self):
        self.is_open = False
        self.visible = False

    # ----------------------------------------------------------------
    # 事件
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open or self._player is None:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                self.close()
                return True

            # 属性分配（1~6）
            attr_keys = [pygame.K_1, pygame.K_2, pygame.K_3,
                        pygame.K_4, pygame.K_5, pygame.K_6]
            if event.key in attr_keys:
                idx = attr_keys.index(event.key)
                if idx < len(ATTR_KEYS):
                    attr_name = ATTR_KEYS[idx]
                    if self._player.build.unspent > 0:
                        self._player.allocate_stat(attr_name, 1)
                return True

            # 上下导航
            if event.key in (pygame.K_w, pygame.K_UP):
                self._selected_attr = (self._selected_attr - 1) % len(ATTR_KEYS)
                return True
            if event.key in (pygame.K_s, pygame.K_DOWN):
                self._selected_attr = (self._selected_attr + 1) % len(ATTR_KEYS)
                return True

        return True

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.is_open or self._player is None:
            return
        self._ensure_fonts()

        # 半透明遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        # ---- 主面板 ----
        pw, ph = 800, 560
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2

        # 背景
        pygame.draw.rect(surface, (22, 20, 34), (px, py, pw, ph), border_radius=8)
        pygame.draw.rect(surface, (70, 65, 90), (px, py, pw, ph), 2, border_radius=8)

        p = self._player

        # ---- 标题 ----
        title_font = get_font(28)
        title_surf = title_font.render("人物属性", True, (230, 210, 160))
        surface.blit(title_surf, (px + 24, py + 14))

        # ---- 等级 + 灵魂 ----
        info_font = get_font(18)
        info_lines = [
            f"Lv.{p.build.level}    灵魂碎片: {p.soul_fragments}    可分配点数: {p.build.unspent}",
        ]
        for i, line in enumerate(info_lines):
            surf = info_font.render(line, True, (200, 200, 215))
            surface.blit(surf, (px + 24, py + 48))

        # ---- 战斗属性（左栏）----
        self._render_combat_stats(surface, px + 24, py + 86)

        # ---- 成长属性（右栏）----
        self._render_growth_attrs(surface, px + 340, py + 86)

        # ---- 装备概览 ----
        self._render_equip_summary(surface, px + 24, py + 380)

        # ---- 底部提示 ----
        hint_font = get_font(15)
        hints = ["1~6: 分配属性点    Tab/ESC: 关闭"]
        for i, h in enumerate(hints):
            surf = hint_font.render(h, True, (140, 135, 160))
            surface.blit(surf, (px + 24, py + ph - 28 + i * 18))

    # ----------------------------------------------------------------
    # 战斗属性渲染
    # ----------------------------------------------------------------

    def _render_combat_stats(self, surface: pygame.Surface, x: int, y: int):
        """渲染战斗衍生属性"""
        p = self._player
        stats = p.stats
        growth = p.growth

        font = get_font(17)
        label_font = get_font(17)
        equip = getattr(p, "equipment", None)

        total_def = equip.total_defense if equip else 0
        total_poi = equip.total_poise if equip else 0.0

        lines = [
            ("生命值",  f"{stats.hp}/{stats.max_hp}",        (200, 60, 60)),
            ("耐力值",  f"{stats.stamina:.0f}/{stats.max_stamina:.0f}", (60, 180, 80)),
            ("灵力值",  f"{stats.mana}/{stats.max_mana}",     (60, 100, 220)),
            ("", "", (0,0,0)),  # 空行
            ("物理攻击", str(stats.atk),                      (220, 200, 100)),
            ("物理防御", str(total_def),                       (160, 160, 200)),
            ("韧  性",  f"{total_poi:.0f}",                    (180, 160, 220)),
            ("", "", (0,0,0)),
            ("负重率",  f"{growth.equip_load_ratio*100:.0f}%", (180, 180, 180)),
        ]

        for label, value, color in lines:
            if not label:
                y += 10
                continue
            lbl = label_font.render(label, True, (160, 155, 180))
            val = font.render(value, True, color)
            surface.blit(lbl, (x, y))
            surface.blit(val, (x + 100, y))
            y += 24

        # 翻滚类型
        roll = growth.roll_type
        roll_name, roll_color = ROLL_NAMES.get(roll, (roll, (180, 180, 180)))
        roll_lbl = label_font.render("翻滚类型", True, (160, 155, 180))
        roll_val = font.render(roll_name, True, roll_color)
        surface.blit(roll_lbl, (x, y))
        surface.blit(roll_val, (x + 100, y))

    # ----------------------------------------------------------------
    # 成长属性渲染
    # ----------------------------------------------------------------

    def _render_growth_attrs(self, surface: pygame.Surface, x: int, y: int):
        """渲染六项成长属性"""
        p = self._player
        title_font = get_font(18, bold=True)
        title_surf = title_font.render("成长属性", True, (200, 190, 140))
        surface.blit(title_surf, (x, y - 26))

        attr_font = get_font(18)
        desc_font = get_font(14)

        for i, key in enumerate(ATTR_KEYS):
            name, desc, color = ATTR_DISPLAY[key]
            val = getattr(p.growth, key, 0)
            ry = y + i * 56

            # 行背景
            if i == self._selected_attr and p.build.unspent > 0:
                bg_color = (55, 48, 70)
                border_color = (100, 90, 140)
            else:
                bg_color = (35, 32, 48) if i % 2 == 0 else (30, 27, 40)
                border_color = None

            row_rect = pygame.Rect(x, ry, 420, 50)
            pygame.draw.rect(surface, bg_color, row_rect, border_radius=4)
            if border_color:
                pygame.draw.rect(surface, border_color, row_rect, 2, border_radius=4)

            # 编号
            num_surf = get_font(13).render(f"[{i+1}]", True, (130, 130, 150))
            surface.blit(num_surf, (x + 6, ry + 17))

            # 属性名
            name_surf = attr_font.render(f"{name}  {val:>2}", True, color)
            surface.blit(name_surf, (x + 36, ry + 4))

            # 描述
            desc_surf = desc_font.render(desc, True, (130, 130, 155))
            surface.blit(desc_surf, (x + 36, ry + 28))

            # 加号按钮（可分配点 > 0）
            if p.build.unspent > 0:
                plus_surf = get_font(22).render("[+]", True, (120, 240, 120))
                surface.blit(plus_surf, (x + 380, ry + 12))

        # 当前状态异常
        self._render_status_effects(surface, x, y + len(ATTR_KEYS) * 56 + 10)

    def _render_status_effects(self, surface: pygame.Surface, x: int, y: int):
        """渲染当前状态异常"""
        p = self._player
        sm = getattr(p.stats, "_status_manager", None)
        if sm is None:
            return

        active_effects = []
        for name in ["bleed", "poison", "burn", "freeze", "curse", "stun"]:
            eff = getattr(sm, f"_{name}", None)
            if eff and getattr(eff, "active", False):
                active_effects.append(name)

        if not active_effects:
            return

        font = get_font(15)
        lbl = font.render("状态异常:", True, (200, 150, 150))
        surface.blit(lbl, (x, y))

        status_colors = {
            "bleed": (200, 30, 60), "poison": (100, 200, 50),
            "burn": (255, 100, 20), "freeze": (80, 200, 255),
            "curse": (150, 50, 200), "stun": (255, 230, 50),
        }
        for i, name in enumerate(active_effects):
            color = status_colors.get(name, (200, 200, 200))
            surf = font.render(name.upper(), True, color)
            surface.blit(surf, (x + 100 + i * 70, y))

    # ----------------------------------------------------------------
    # 装备概览
    # ----------------------------------------------------------------

    def _render_equip_summary(self, surface: pygame.Surface, x: int, y: int):
        """渲染当前装备一览"""
        p = self._player
        font = get_font(15)

        # 武器
        weapon = getattr(p, "weapon", None)
        if weapon:
            wpn_name = getattr(weapon, "display_name", "武器")
            wpn_lv = getattr(weapon, "upgrade_level", 0)
            wpn_text = f"武器: {wpn_name} +{wpn_lv}"
        else:
            wpn_text = "武器: 无"

        wpn_surf = font.render(wpn_text, True, (220, 200, 120))
        surface.blit(wpn_surf, (x, y))

        # 护甲
        equip = getattr(p, "equipment", None)
        armor_slots = {"head": "头", "chest": "胸", "hands": "手", "legs": "腿"}
        parts = []
        if equip:
            for slot, label in armor_slots.items():
                item = equip.get(slot)
                if item:
                    parts.append(f"{label}:{item.name[:4]}")
                else:
                    parts.append(f"{label}:--")
        if parts:
            armor_text = "  ".join(parts)
            armor_surf = font.render(armor_text, True, (160, 180, 210))
            surface.blit(armor_surf, (x, y + 22))

        # 套装
        if equip:
            set_info = getattr(equip, "active_set", None)
            if set_info:
                set_surf = font.render(f"套装: {set_info}", True, (255, 215, 80))
                surface.blit(set_surf, (x, y + 44))

    # ----------------------------------------------------------------
    # 字体
    # ----------------------------------------------------------------

    _fonts_ready = False

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._fonts_ready = True
