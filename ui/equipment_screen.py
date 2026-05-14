# =============================================================
# ui/equipment_screen.py —— 装备界面
#
# 展示人形 6 个槽位 + 当前属性面板。
# 按 E 键打开/关闭（与背包界面独立，可同时打开）。
#
# 布局：
#   左区：人形轮廓 + 6 个槽位示意（头/胸/手/腿/武器/盾）
#   右区：当前属性面板（HP / Stamina / Mana / ATK / DEF / 韧性 / 负重 / 翻滚类型）
# =============================================================
from __future__ import annotations
import pygame
from typing import Optional, TYPE_CHECKING

from ui.font_manager import get_font

if TYPE_CHECKING:
    from entities.player.player import Player
    from player.equipment import Equipment


# ---- 布局常量 ----
PANEL_LEFT  = 60
PANEL_TOP   = 60
PANEL_W     = 740
PANEL_H     = 600    # 增大高度，容纳所有属性行

# 人形中心
FIGURE_CX   = PANEL_LEFT + 210
FIGURE_CY   = PANEL_TOP  + 270

# 各槽位相对人形中心的偏移（cx, cy, label）
_SLOT_POS = {
    "head":   (FIGURE_CX,        FIGURE_CY - 170, "头"),
    "chest":  (FIGURE_CX,        FIGURE_CY - 70,  "胸"),
    "hands":  (FIGURE_CX - 110,  FIGURE_CY - 60,  "手"),
    "legs":   (FIGURE_CX,        FIGURE_CY + 60,  "腿"),
    "weapon": (FIGURE_CX - 110,  FIGURE_CY + 70,  "武"),
    "shield": (FIGURE_CX + 110,  FIGURE_CY + 70,  "盾"),
}

SLOT_W = 72
SLOT_H = 60

# 属性面板
STAT_LEFT = PANEL_LEFT + 430
STAT_TOP  = PANEL_TOP  + 16
STAT_LINE = 26   # 行高缩小，确保所有行都在面板内

# ---- 配色 ----
COLOR_BG         = (18, 16, 26)
COLOR_BORDER     = (60, 55, 80)
COLOR_TITLE      = (230, 210, 160)
COLOR_TEXT       = (200, 195, 215)
COLOR_HINT       = (140, 135, 160)
COLOR_SLOT_EMPTY = (40, 38, 55)
COLOR_SLOT_FILL  = (65, 60, 90)
COLOR_SLOT_HOVER = (90, 85, 130)
COLOR_FIGURE     = (55, 52, 75)
COLOR_STAT_LABEL = (160, 158, 180)
COLOR_STAT_VALUE = (230, 220, 160)
COLOR_DETAIL_LINE = (60, 55, 80)   # 属性分割线颜色

# 属性面板宽度（用于分割线计算）
DETAIL_W = PANEL_W - (STAT_LEFT - PANEL_LEFT)

# 翻滚类型颜色
ROLL_COLORS = {
    "fast":   (100, 220, 150),
    "normal": (200, 200, 100),
    "slow":   (220, 150,  80),
    "unable": (220,  80,  80),
}
ROLL_NAMES = {
    "fast":   "快速翻滚",
    "normal": "普通翻滚",
    "slow":   "慢速翻滚",
    "unable": "无法翻滚",
}


class EquipmentScreen:
    """
    装备界面。

    集成到 GameScene：
        self._equip_screen = EquipmentScreen()

        # handle_events
        if event.key == pygame.K_e:
            self._equip_screen.toggle(self._player)
        if self._equip_screen.is_open:
            self._equip_screen.handle_event(event)

        # render（最后调用，覆盖在游戏画面之上）
        self._equip_screen.render(surface)
    """

    def __init__(self):
        self.is_open:    bool               = False
        self._player:    Optional["Player"] = None
        self._hover_slot: Optional[str]     = None

        self._font_title  = None
        self._font_label  = None
        self._font_stat   = None
        self._font_hint   = None
        self._fonts_ready = False

    # ----------------------------------------------------------------
    # 字体懒加载
    # ----------------------------------------------------------------

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title  = get_font(20, bold=True)
            self._font_label  = get_font(13)
            self._font_stat   = get_font(15)    # 缩小属性字号，防止溢出
            self._font_hint   = get_font(13)
            self._fonts_ready = True

    # ----------------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------------

    def toggle(self, player: "Player"):
        self.is_open = not self.is_open
        if self.is_open:
            self._player    = player
            self._hover_slot = None

    def open(self, player: "Player"):
        self.is_open     = True
        self._player     = player
        self._hover_slot = None

    def close(self):
        self.is_open = False

    # ----------------------------------------------------------------
    # 事件
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_e, pygame.K_ESCAPE):
                self.close()
                return True
            # U 键卸下悬停槽位的装备
            if event.key == pygame.K_u and self._hover_slot:
                self._action_unequip(self._hover_slot)
                return True

        elif event.type == pygame.MOUSEMOTION:
            self._hover_slot = self._pos_to_slot(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3:   # 右键卸下
                slot = self._pos_to_slot(event.pos)
                if slot:
                    self._action_unequip(slot)
                    return True

        return False

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface):
        if not self.is_open or self._player is None:
            return

        self._ensure_fonts()

        # ---- 半透明遮罩 ----
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        # ---- 面板背景 ----
        panel_rect = pygame.Rect(PANEL_LEFT, PANEL_TOP, PANEL_W, PANEL_H)
        pygame.draw.rect(surface, COLOR_BG, panel_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, panel_rect, 2, border_radius=8)

        # ---- 标题 ----
        title_surf = self._font_title.render("装  备", True, COLOR_TITLE)
        surface.blit(title_surf, (PANEL_LEFT + 16, PANEL_TOP + 12))

        # ---- 人形轮廓 ----
        self._render_figure(surface)

        # ---- 6 个槽位 ----
        self._render_slots(surface)

        # ---- 属性面板 ----
        self._render_stats(surface)

        # ---- 底部提示 ----
        self._render_hints(surface)

    # ----------------------------------------------------------------
    # 人形轮廓
    # ----------------------------------------------------------------

    def _render_figure(self, surface: pygame.Surface):
        cx, cy = FIGURE_CX, FIGURE_CY
        # 简单几何人形
        # 头
        pygame.draw.circle(surface, COLOR_FIGURE, (cx, cy - 140), 22)
        # 躯干
        pygame.draw.rect(surface, COLOR_FIGURE,
                         pygame.Rect(cx - 28, cy - 115, 56, 90), border_radius=4)
        # 左臂
        pygame.draw.rect(surface, COLOR_FIGURE,
                         pygame.Rect(cx - 58, cy - 112, 28, 70), border_radius=4)
        # 右臂
        pygame.draw.rect(surface, COLOR_FIGURE,
                         pygame.Rect(cx + 30, cy - 112, 28, 70), border_radius=4)
        # 左腿
        pygame.draw.rect(surface, COLOR_FIGURE,
                         pygame.Rect(cx - 30, cy - 24, 26, 85), border_radius=4)
        # 右腿
        pygame.draw.rect(surface, COLOR_FIGURE,
                         pygame.Rect(cx + 4, cy - 24, 26, 85), border_radius=4)

    # ----------------------------------------------------------------
    # 槽位渲染
    # ----------------------------------------------------------------

    def _render_slots(self, surface: pygame.Surface):
        equip: Optional["Equipment"] = getattr(self._player, "equipment", None)

        for slot_name, (cx, cy, label) in _SLOT_POS.items():
            rect = pygame.Rect(cx - SLOT_W // 2, cy - SLOT_H // 2, SLOT_W, SLOT_H)

            is_hover = (slot_name == self._hover_slot)
            item = equip.get(slot_name) if equip else None

            # 背景
            bg_color = COLOR_SLOT_HOVER if is_hover else (COLOR_SLOT_FILL if item else COLOR_SLOT_EMPTY)
            pygame.draw.rect(surface, bg_color, rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_BORDER, rect, 1, border_radius=4)

            # 槽位标签
            lbl_surf = self._font_label.render(label, True, COLOR_HINT)
            surface.blit(lbl_surf, (rect.left + 4, rect.top + 4))

            if item:
                # 物品名
                name_text = item.name[:5]
                name_surf = self._font_label.render(name_text, True, COLOR_TEXT)
                nx = rect.centerx - name_surf.get_width() // 2
                ny = rect.centery - name_surf.get_height() // 2 + 8
                surface.blit(name_surf, (nx, ny))
            else:
                empty_surf = self._font_label.render("（空）", True, COLOR_HINT)
                ex = rect.centerx - empty_surf.get_width() // 2
                ey = rect.centery - empty_surf.get_height() // 2 + 8
                surface.blit(empty_surf, (ex, ey))

    # ----------------------------------------------------------------
    # 属性面板
    # ----------------------------------------------------------------

    def _render_stats(self, surface: pygame.Surface):
        p      = self._player
        stats  = p.stats
        growth = p.growth
        equip: Optional["Equipment"] = getattr(p, "equipment", None)

        # 分割线
        pygame.draw.line(surface, COLOR_BORDER,
                         (STAT_LEFT - 20, PANEL_TOP + 10),
                         (STAT_LEFT - 20, PANEL_TOP + PANEL_H - 10), 1)

        title = self._font_title.render("属  性", True, COLOR_TITLE)
        surface.blit(title, (STAT_LEFT, STAT_TOP))

        ty = STAT_TOP + 36
        # 面板底部留 30px 给提示文字
        max_ty = PANEL_TOP + PANEL_H - 30

        def draw_stat(label: str, value: str, color=COLOR_STAT_VALUE):
            nonlocal ty
            if ty + STAT_LINE > max_ty:
                return   # 超出面板范围则不绘制
            lbl  = self._font_stat.render(label, True, COLOR_STAT_LABEL)
            val  = self._font_stat.render(value, True, color)
            surface.blit(lbl, (STAT_LEFT, ty))
            surface.blit(val, (STAT_LEFT + 130, ty))
            ty += STAT_LINE

        def draw_divider():
            nonlocal ty
            if ty + 8 > max_ty:
                return
            pygame.draw.line(surface, COLOR_DETAIL_LINE,
                             (STAT_LEFT, ty + 3),
                             (STAT_LEFT + DETAIL_W - 20, ty + 3), 1)
            ty += 10

        draw_stat("生命值",  f"{stats.hp} / {stats.max_hp}")
        draw_stat("耐力值",  f"{stats.stamina:.0f} / {stats.max_stamina:.0f}")
        draw_stat("灵力值",  f"{stats.mana} / {stats.max_mana}")
        draw_divider()

        total_def = equip.total_defense if equip else 0
        total_poi = equip.total_poise   if equip else 0.0
        weapon_base = getattr(p.weapon, "_base_light_dmg", 0) if p.weapon else 0
        draw_stat("物理攻击", str(stats.atk + weapon_base))
        draw_stat("物理防御", str(total_def))
        draw_stat("韧  性",   f"{total_poi:.0f}")
        draw_divider()

        draw_stat("当前负重",
                  f"{growth.equip_weight:.1f}/{growth.max_equip_load:.1f}kg")
        load_pct = growth.equip_load_ratio * 100
        draw_stat("负重  率", f"{load_pct:.0f}%")

        # 翻滚类型（彩色）
        roll = growth.roll_type
        roll_color = ROLL_COLORS.get(roll, COLOR_STAT_VALUE)
        draw_stat("翻滚类型", ROLL_NAMES.get(roll, roll), color=roll_color)
        draw_divider()

        # 成长属性摘要
        attrs = [
            ("力量", growth.strength),
            ("敏捷", growth.dexterity),
            ("智慧", growth.intelligence),
            ("信仰", growth.faith),
            ("体魄", growth.vitality),
            ("耐性", growth.endurance),
        ]
        for label, val in attrs:
            draw_stat(label, str(val))

    # ----------------------------------------------------------------
    # 底部提示
    # ----------------------------------------------------------------

    def _render_hints(self, surface: pygame.Surface):
        from config import SCREEN_HEIGHT
        hints = "右键 / U: 卸下装备    E / ESC: 关闭"
        hint_surf = self._font_hint.render(hints, True, COLOR_HINT)
        surface.blit(hint_surf, (PANEL_LEFT + 12, PANEL_TOP + PANEL_H - hint_surf.get_height() - 12))

    # ----------------------------------------------------------------
    # 操作
    # ----------------------------------------------------------------

    def _action_unequip(self, slot: str):
        """卸下指定槽位装备，放回背包。"""
        if self._player is None:
            return
        equip = getattr(self._player, "equipment", None)
        inv   = getattr(self._player, "inventory", None)
        if equip is None or inv is None:
            return

        old_item = equip.unequip(slot)
        if old_item is not None:
            inv.add(old_item, 1)

    # ----------------------------------------------------------------
    # 鼠标位置 → 槽位名
    # ----------------------------------------------------------------

    def _pos_to_slot(self, pos: tuple[int, int]) -> Optional[str]:
        mx, my = pos
        for slot_name, (cx, cy, _label) in _SLOT_POS.items():
            rx = cx - SLOT_W // 2
            ry = cy - SLOT_H // 2
            if rx <= mx < rx + SLOT_W and ry <= my < ry + SLOT_H:
                return slot_name
        return None
