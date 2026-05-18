# =============================================================
# ui/inventory_screen.py —— 背包界面
#
# 按 I 键打开/关闭。打开时暂停游戏逻辑（不调用 update）。
#
# 布局：
#   左区  ：6×5 物品网格（30格）
#   右区  ：悬停物品的详情面板
#   底部  ：操作提示（E装备/使用  Q丢弃  ESC/I关闭）
#
# 中文文字全部使用 get_font() 渲染。
# =============================================================
from __future__ import annotations
import pygame
from typing import Optional, TYPE_CHECKING

from ui.font_manager import get_font
from ui.base_widget import BaseWidget
from items.item_base import ItemType

if TYPE_CHECKING:
    from player.inventory import Inventory, InventorySlot
    from entities.player.player import Player


# ---- 布局常量 ----
GRID_COLS     = 6
GRID_ROWS     = 5
CELL_SIZE     = 60     # 每格像素大小（缩小4px，整体网格宽 = 6×60+5×6 = 390）
CELL_PAD      = 6      # 格间距
GRID_LEFT     = 60
GRID_TOP      = 100

# 网格总宽 = COLS * CELL_SIZE + (COLS-1) * CELL_PAD = 6*60 + 5*6 = 390
DETAIL_LEFT   = GRID_LEFT + (CELL_SIZE + CELL_PAD) * GRID_COLS + 24
DETAIL_TOP    = GRID_TOP
DETAIL_W      = 280
DETAIL_H      = 400

# ---- 配色 ----
COLOR_BG          = (20, 18, 28, 220)   # 半透明深色背景
COLOR_CELL_NORMAL = (45, 42, 60)
COLOR_CELL_HOVER  = (80, 75, 110)
COLOR_CELL_SELECT = (110, 100, 160)
COLOR_CELL_BORDER = (80,  78, 100)
COLOR_TITLE       = (230, 210, 160)
COLOR_TEXT        = (200, 195, 215)
COLOR_HINT        = (140, 135, 160)
COLOR_DETAIL_BG   = (30, 27, 42)
COLOR_DETAIL_LINE = (60, 55, 80)
COLOR_ITEM_WEAPON = (200, 180, 100)
COLOR_ITEM_ARMOR  = (130, 180, 220)
COLOR_ITEM_CONS   = (120, 210, 140)
COLOR_ITEM_MISC   = (180, 180, 180)

_TYPE_COLOR = {
    ItemType.WEAPON:     COLOR_ITEM_WEAPON,
    ItemType.ARMOR:      COLOR_ITEM_ARMOR,
    ItemType.CONSUMABLE: COLOR_ITEM_CONS,
    ItemType.MISC:       COLOR_ITEM_MISC,
}


class InventoryScreen(BaseWidget):
    """
    背包界面（覆盖层，不替换场景）。
    由 GameScene.handle_events 负责创建并传入事件；
    GameScene.update 在 is_open 为 True 时跳过 player.update。
    GameScene.render 在正常渲染后调用 inventory_screen.render()。

    典型集成：
        # game_scene.py
        self._inv_screen = InventoryScreen()

        # handle_events
        if event.key == pygame.K_i:
            self._inv_screen.toggle(self._player)
        if self._inv_screen.is_open:
            self._inv_screen.handle_event(event)

        # update
        if not self._inv_screen.is_open:
            self._player.update(dt, ...)

        # render（最后调用）
        self._inv_screen.render(surface)
    """

    def __init__(self):
        super().__init__(visible=False, z_index=50)
        self.is_open:       bool            = False
        self._player:       Optional["Player"] = None
        self._hover_idx:    int             = -1   # 鼠标悬停格
        self._selected_idx: int             = -1   # 键盘/点击选中格

        self._font_title  = None
        self._font_item   = None
        self._font_detail = None
        self._font_hint   = None
        self._fonts_ready = False

    # ----------------------------------------------------------------
    # 字体懒加载（pygame.font 必须在 init 后才能调用）
    # ----------------------------------------------------------------

    def _ensure_fonts(self):
        if not self._fonts_ready:
            self._font_title  = get_font(22, bold=True)
            self._font_item   = get_font(14)
            self._font_detail = get_font(16)
            self._font_hint   = get_font(14)
            self._fonts_ready = True

    # ----------------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------------

    def toggle(self, player: "Player"):
        """切换背包开/关。"""
        self.is_open = not self.is_open
        self.visible = self.is_open
        if self.is_open:
            self._player = player
            self._hover_idx    = -1
            self._selected_idx = -1

    def open(self, player: "Player"):
        self.is_open   = True
        self.visible   = True
        self._player   = player
        self._hover_idx    = -1
        self._selected_idx = -1

    def close(self):
        self.is_open = False
        self.visible = False

    # ----------------------------------------------------------------
    # 事件处理
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        处理输入事件。
        返回 True 表示事件已被消耗（上层不再处理）。
        """
        if not self.is_open:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_i, pygame.K_ESCAPE):
                self.close()
                return True
            if event.key == pygame.K_e and self._selected_idx >= 0:
                self._action_equip_or_use(self._selected_idx)
                return True
            if event.key == pygame.K_q and self._selected_idx >= 0:
                self._action_drop(self._selected_idx)
                return True

        elif event.type == pygame.MOUSEMOTION:
            self._hover_idx = self._pos_to_slot(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:   # 左键：选中
                clicked = self._pos_to_slot(event.pos)
                if clicked >= 0:
                    self._selected_idx = clicked
                    return True
            elif event.button == 3: # 右键：快速使用/装备
                clicked = self._pos_to_slot(event.pos)
                if clicked >= 0:
                    self._action_equip_or_use(clicked)
                    return True

        return False

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface):
        if not self.is_open or self._player is None:
            return

        self._ensure_fonts()
        inv = getattr(self._player, "inventory", None)
        if inv is None:
            return

        # ---- 半透明遮罩 ----
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # ---- 标题 ----
        title_surf = self._font_title.render("背  包", True, COLOR_TITLE)
        surface.blit(title_surf, (GRID_LEFT, GRID_TOP - 50))

        # ---- 格子网格 ----
        self._render_grid(surface, inv)

        # ---- 详情面板 ----
        self._render_detail(surface, inv)

        # ---- 底部提示 ----
        self._render_hints(surface)

    # ----------------------------------------------------------------
    # 网格渲染
    # ----------------------------------------------------------------

    def _render_grid(self, surface: pygame.Surface, inv: "Inventory"):
        for idx in range(30):
            col = idx % GRID_COLS
            row = idx // GRID_COLS
            x = GRID_LEFT + col * (CELL_SIZE + CELL_PAD)
            y = GRID_TOP  + row * (CELL_SIZE + CELL_PAD)
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

            # 背景色
            if idx == self._selected_idx:
                bg_color = COLOR_CELL_SELECT
            elif idx == self._hover_idx:
                bg_color = COLOR_CELL_HOVER
            else:
                bg_color = COLOR_CELL_NORMAL

            pygame.draw.rect(surface, bg_color, rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_CELL_BORDER, rect, 1, border_radius=4)

            slot = inv.get_slot(idx)
            if slot is None:
                continue

            # 物品颜色块（临时图标）
            item = slot.item
            icon_color = _TYPE_COLOR.get(item.item_type, COLOR_ITEM_MISC)
            icon_rect = pygame.Rect(x + 6, y + 6, CELL_SIZE - 12, CELL_SIZE - 24)
            pygame.draw.rect(surface, icon_color, icon_rect, border_radius=3)

            # 物品名称（截断到格宽）
            name_surf = self._font_item.render(item.name[:4], True, COLOR_TEXT)
            surface.blit(name_surf, (x + 4, y + CELL_SIZE - 20))

            # 叠加数量
            if item.stackable and slot.quantity > 1:
                qty_str  = str(slot.quantity)
                qty_surf = self._font_item.render(qty_str, True, (255, 230, 100))
                surface.blit(qty_surf, (x + CELL_SIZE - qty_surf.get_width() - 4, y + 4))

    # ----------------------------------------------------------------
    # 详情面板渲染
    # ----------------------------------------------------------------

    def _render_detail(self, surface: pygame.Surface, inv: "Inventory"):
        # 背景
        detail_rect = pygame.Rect(DETAIL_LEFT, DETAIL_TOP, DETAIL_W, DETAIL_H)
        pygame.draw.rect(surface, COLOR_DETAIL_BG, detail_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_CELL_BORDER, detail_rect, 1, border_radius=6)

        # 分割线
        pygame.draw.line(surface, COLOR_DETAIL_LINE,
                         (DETAIL_LEFT + 10, DETAIL_TOP + 36),
                         (DETAIL_LEFT + DETAIL_W - 10, DETAIL_TOP + 36), 1)

        # 查找要展示的格子：优先 selected，其次 hover
        show_idx = self._selected_idx if self._selected_idx >= 0 else self._hover_idx
        slot = inv.get_slot(show_idx) if show_idx >= 0 else None

        if slot is None:
            hint = self._font_detail.render("（悬停物品查看详情）", True, COLOR_HINT)
            surface.blit(hint, (DETAIL_LEFT + 12, DETAIL_TOP + 50))
            return

        item = slot.item
        lines = item.get_tooltip_lines()

        # 第一行：物品名（加粗字号）
        title_surf = self._font_title.render(lines[0], True, COLOR_TITLE)
        surface.blit(title_surf, (DETAIL_LEFT + 12, DETAIL_TOP + 8))

        # 其余行
        ty = DETAIL_TOP + 46
        for line in lines[1:]:
            text_surf = self._font_detail.render(line, True, COLOR_TEXT)
            surface.blit(text_surf, (DETAIL_LEFT + 12, ty))
            ty += text_surf.get_height() + 6

        # 叠加数量
        if slot.item.stackable:
            qty_line = f"持有: {slot.quantity} / {slot.item.max_stack}"
            qty_surf = self._font_detail.render(qty_line, True, COLOR_HINT)
            surface.blit(qty_surf, (DETAIL_LEFT + 12, ty + 4))

    # ----------------------------------------------------------------
    # 底部提示
    # ----------------------------------------------------------------

    def _render_hints(self, surface: pygame.Surface):
        from config import SCREEN_HEIGHT
        hints = "E: 装备/使用    Q: 丢弃    I / ESC: 关闭"
        hint_surf = self._font_hint.render(hints, True, COLOR_HINT)
        x = GRID_LEFT
        y = SCREEN_HEIGHT - hint_surf.get_height() - 20
        surface.blit(hint_surf, (x, y))

    # ----------------------------------------------------------------
    # 操作
    # ----------------------------------------------------------------

    def _action_equip_or_use(self, idx: int):
        """对选中格执行装备（武器/护甲）或使用（消耗品）。"""
        if self._player is None:
            return
        inv = getattr(self._player, "inventory", None)
        equip = getattr(self._player, "equipment", None)
        if inv is None:
            return

        slot = inv.get_slot(idx)
        if slot is None:
            return

        item = slot.item

        if item.item_type == ItemType.CONSUMABLE:
            # 使用消耗品
            ok = inv.use_item(idx, self._player)
            if ok:
                self._selected_idx = -1

        elif item.item_type in (ItemType.WEAPON, ItemType.ARMOR):
            if equip is None:
                return
            # 确定目标槽位
            from items.weapon import WeaponItem
            from items.armor  import ArmorItem
            from player.equipment import SLOT_WEAPON, _ARMOR_SLOT_MAP

            if isinstance(item, WeaponItem):
                target_slot = SLOT_WEAPON
            elif isinstance(item, ArmorItem):
                target_slot = _ARMOR_SLOT_MAP.get(item.slot)
            else:
                return

            if target_slot is None:
                return

            # 从背包移除，装备到装备栏（旧装备放回背包）
            inv.remove(idx, 1)
            old_item = equip.equip(target_slot, item)
            if old_item is not None:
                inv.add(old_item, 1)

            self._selected_idx = -1

    def _action_drop(self, idx: int):
        """丢弃选中格的1件物品。"""
        if self._player is None:
            return
        inv = getattr(self._player, "inventory", None)
        if inv is None:
            return
        inv.drop_item(idx, 1)
        self._selected_idx = -1

    # ----------------------------------------------------------------
    # 鼠标位置 → 格子索引
    # ----------------------------------------------------------------

    def _pos_to_slot(self, pos: tuple[int, int]) -> int:
        """将屏幕坐标转换为背包格子索引，不在格内返回 -1。"""
        mx, my = pos
        for idx in range(30):
            col = idx % GRID_COLS
            row = idx // GRID_COLS
            x = GRID_LEFT + col * (CELL_SIZE + CELL_PAD)
            y = GRID_TOP  + row * (CELL_SIZE + CELL_PAD)
            if x <= mx < x + CELL_SIZE and y <= my < y + CELL_SIZE:
                return idx
        return -1
