# =============================================================
# ui/shop_screen.py —— 商店界面（购买消耗品/武器/护甲）
#
# 第 11 阶段扩展：商人 NPC 的完整购买界面。
#
# 打开时暂停游戏逻辑（同 InventoryScreen/CampfireMenu 模式）。
# 数据来源：data/items/shop_merchant.json
#
# 操作：
#   W/S ↑↓    选择商品
#   Q/E ←→    切换分类（消耗品 / 武器 / 护甲）
#   Enter      购买
#   ESC / F    离开商店
#
# 布局：
#   左上 ：NPC 名称 + 问候语
#   中左 ：分类标签 + 商品列表
#   中右 ：物品详情面板
#   底部 ：灵魂碎片数 + 操作提示 + 消息
# =============================================================
from __future__ import annotations

import os
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import pygame

from ui.font_manager import get_font
from utils.color import UI_HIGHLIGHT, WHITE
from items.item_base import ItemType
from config import SCREEN_WIDTH, SCREEN_HEIGHT, DATA_DIR

if TYPE_CHECKING:
    from entities.player.player import Player


# ---- 布局常量 ----
PANEL_W      = 820
PANEL_H      = 540
PANEL_X      = (SCREEN_WIDTH  - PANEL_W) // 2
PANEL_Y      = (SCREEN_HEIGHT - PANEL_H) // 2

LIST_LEFT    = 24
LIST_TOP     = 110
LIST_W       = 380
LIST_ROW_H   = 32
LIST_VISIBLE = 12

DETAIL_LEFT  = PANEL_W - 360
DETAIL_TOP   = LIST_TOP
DETAIL_W     = 320

# ---- 配色 ----
COLOR_OVERLAY    = (0, 0, 0, 150)
COLOR_PANEL_BG   = (25, 22, 35)
COLOR_PANEL_BD   = (80, 75, 100)
COLOR_TAB_ACTIVE = (80, 70, 110)
COLOR_TAB_INACT  = (40, 36, 55)
COLOR_TAB_TEXT   = (180, 175, 200)
COLOR_ROW_HOVER  = (65, 58, 85)
COLOR_ROW_PRICE  = (255, 220, 100)
COLOR_ROW_NAME   = (210, 205, 225)
COLOR_MSG_OK     = (120, 240, 140)
COLOR_MSG_ERR    = (240, 140, 140)
COLOR_DETAIL_BG  = (32, 28, 44)


class ShopScreen:
    """
    商店购买界面（覆盖层）。
    """

    def __init__(self):
        self.is_open: bool = False
        self._player: Optional["Player"] = None

        # 商店数据（从 JSON 加载）
        self._categories: List[Dict[str, Any]] = []
        self._npc_name: str = "商人"
        self._greeting: str = ""

        # 分类索引
        self._category_idx: int = 0
        # 商品列表索引
        self._item_idx: int = 0

        # 消息提示
        self._message: str = ""
        self._msg_timer: float = 0.0

        # 字体缓存
        self._fonts: Dict[str, pygame.font.Font] = {}

        self._load_data()

    # ----------------------------------------------------------------
    # 数据加载
    # ----------------------------------------------------------------

    def _load_data(self) -> None:
        """从 JSON 加载商店数据。"""
        import json
        path = os.path.join(DATA_DIR, "items", "shop_merchant.json")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self._categories = data.get("categories", [])
            self._npc_name = data.get("npc_name", "商人")
            self._greeting = data.get("greeting", "")
        except Exception:
            self._categories = []
            self._npc_name = "商人"
            self._greeting = ""

    # ----------------------------------------------------------------
    # 生命期
    # ----------------------------------------------------------------

    def open(self, player: "Player") -> None:
        self.is_open = True
        self._player = player
        self._category_idx = 0
        self._item_idx = 0
        self._message = ""
        self._msg_timer = 0.0

    def close(self) -> None:
        self.is_open = False
        self._player = None

    # ----------------------------------------------------------------
    # 事件处理
    # ----------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件，返回 True 表示消耗。"""
        if not self.is_open:
            return False

        if event.type != pygame.KEYDOWN:
            return True

        key = event.key

        # 离开
        if key == pygame.K_ESCAPE or key == pygame.K_f:
            self.close()
            return True

        # 切换分类
        if key == pygame.K_q or key == pygame.K_LEFT:
            self._category_idx = (self._category_idx - 1) % max(1, len(self._categories))
            self._item_idx = 0
            return True
        if key == pygame.K_e or key == pygame.K_RIGHT:
            self._category_idx = (self._category_idx + 1) % max(1, len(self._categories))
            self._item_idx = 0
            return True

        # 选择商品
        cat = self._current_category()
        item_count = len(cat) if cat else 0

        if key == pygame.K_w or key == pygame.K_UP:
            self._item_idx = (self._item_idx - 1) % max(1, item_count)
            return True
        if key == pygame.K_s or key == pygame.K_DOWN:
            self._item_idx = (self._item_idx + 1) % max(1, item_count)
            return True

        # 购买
        if key == pygame.K_RETURN or key == pygame.K_SPACE:
            self._do_buy()
            return True

        return True

    # ----------------------------------------------------------------
    # 更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self._msg_timer > 0:
            self._msg_timer = max(0.0, self._msg_timer - dt)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.is_open:
            return

        # 半透明遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        surface.blit(overlay, (0, 0))

        px, py = PANEL_X, PANEL_Y

        # 面板背景
        pygame.draw.rect(surface, COLOR_PANEL_BG, (px, py, PANEL_W, PANEL_H))
        pygame.draw.rect(surface, COLOR_PANEL_BD, (px, py, PANEL_W, PANEL_H), 2)

        # ---- 标题 ----
        title_font = self._font(28)
        title_s = title_font.render(self._npc_name, True, UI_HIGHLIGHT)
        surface.blit(title_s, (px + PANEL_W // 2 - title_s.get_width() // 2, py + 14))

        # 问候语
        if self._greeting:
            greet_font = self._font(16)
            greet_s = greet_font.render(self._greeting, True, (170, 165, 190))
            surface.blit(greet_s, (px + PANEL_W // 2 - greet_s.get_width() // 2, py + 48))

        # ---- 分类标签 ----
        self._render_tabs(surface, px, py)

        # ---- 商品列表 (左) ----
        self._render_item_list(surface, px, py)

        # ---- 物品详情 (右) ----
        self._render_detail(surface, px, py)

        # ---- 底部：灵魂 + 提示 + 消息 ----
        self._render_bottom(surface, px, py)

    # ----------------------------------------------------------------
    # 子渲染：分类标签
    # ----------------------------------------------------------------

    def _render_tabs(self, surface: pygame.Surface, px: int, py: int) -> None:
        tab_font = self._font(18)
        tab_y = py + 80
        tab_x_start = px + LIST_LEFT
        tab_w = 100
        tab_h = 28
        gap = 8

        for i, cat in enumerate(self._categories):
            tx = tab_x_start + i * (tab_w + gap)
            is_active = (i == self._category_idx)

            bg = COLOR_TAB_ACTIVE if is_active else COLOR_TAB_INACT
            text_color = UI_HIGHLIGHT if is_active else COLOR_TAB_TEXT

            pygame.draw.rect(surface, bg, (tx, tab_y, tab_w, tab_h))
            pygame.draw.rect(surface, COLOR_PANEL_BD, (tx, tab_y, tab_w, tab_h), 1)

            name = cat.get("name", f"分类{i}")
            ts = tab_font.render(name, True, text_color)
            surface.blit(ts, (tx + tab_w // 2 - ts.get_width() // 2,
                              tab_y + tab_h // 2 - ts.get_height() // 2))

    # ----------------------------------------------------------------
    # 子渲染：商品列表
    # ----------------------------------------------------------------

    def _render_item_list(self, surface: pygame.Surface, px: int, py: int) -> None:
        cat = self._current_category()
        if not cat:
            return

        name_font = self._font(18)
        price_font = self._font(16)
        lx = px + LIST_LEFT
        ly = py + LIST_TOP
        row_h = LIST_ROW_H

        # 可见范围（按选中项居中的滚动）
        total = len(cat)
        start = max(0, self._item_idx - LIST_VISIBLE // 2)
        end = min(total, start + LIST_VISIBLE)
        # 修正 start 以免末尾空白
        if total > LIST_VISIBLE:
            start = max(0, min(start, total - LIST_VISIBLE))
            end = start + LIST_VISIBLE

        # 列表背景
        list_bg_h = LIST_VISIBLE * row_h + 8
        pygame.draw.rect(surface, (20, 18, 28),
                         (lx - 4, ly - 4, LIST_W + 8, list_bg_h))

        for i in range(start, end):
            row_y = ly + (i - start) * row_h
            item = cat[i]

            # 高亮行
            if i == self._item_idx:
                pygame.draw.rect(surface, COLOR_ROW_HOVER,
                                 (lx, row_y, LIST_W, row_h - 2))
                prefix = "▶ "
                name_color = UI_HIGHLIGHT
            else:
                prefix = "  "
                name_color = COLOR_ROW_NAME

            # 物品名称
            display = self._get_item_display_name(item["item_id"])
            ns = name_font.render(f"{prefix}{display}", True, name_color)
            surface.blit(ns, (lx + 8, row_y + row_h // 2 - ns.get_height() // 2))

            # 价格
            price_s = price_font.render(f"{item['price']}魂", True, COLOR_ROW_PRICE)
            surface.blit(price_s, (lx + LIST_W - price_s.get_width() - 12,
                                   row_y + row_h // 2 - price_s.get_height() // 2))

            # 分隔线
            if i < end - 1:
                pygame.draw.line(surface, (40, 37, 55),
                                 (lx + 4, row_y + row_h - 1),
                                 (lx + LIST_W - 4, row_y + row_h - 1))

        # 滚动指示器
        if total > LIST_VISIBLE:
            bar_h = max(20, (LIST_VISIBLE * row_h) * LIST_VISIBLE // total)
            bar_y = ly + (LIST_VISIBLE * row_h - bar_h) * start // max(1, total - LIST_VISIBLE)
            pygame.draw.rect(surface, (80, 75, 100),
                             (lx + LIST_W + 6, bar_y, 4, bar_h))

    # ----------------------------------------------------------------
    # 子渲染：物品详情
    # ----------------------------------------------------------------

    def _render_detail(self, surface: pygame.Surface, px: int, py: int) -> None:
        cat = self._current_category()
        if not cat or self._item_idx >= len(cat):
            return

        item_data = cat[self._item_idx]
        item_id = item_data["item_id"]
        price = item_data["price"]

        dx = px + DETAIL_LEFT
        dy = py + DETAIL_TOP
        dw = DETAIL_W

        # 详情面板背景
        dh = LIST_VISIBLE * LIST_ROW_H + 8
        pygame.draw.rect(surface, COLOR_DETAIL_BG, (dx, dy, dw, dh))
        pygame.draw.rect(surface, COLOR_PANEL_BD, (dx, dy, dw, dh), 1)

        name_font = self._font(22)
        info_font = self._font(16)
        desc_font = self._font(14)

        # 物品名称
        display_name = self._get_item_display_name(item_id)
        ns = name_font.render(display_name, True, UI_HIGHLIGHT)
        surface.blit(ns, (dx + 16, dy + 12))

        # 价格
        ps = info_font.render(f"价格: {price} 灵魂碎片", True, COLOR_ROW_PRICE)
        surface.blit(ps, (dx + 16, dy + 42))

        # 类型
        kind = self._get_item_kind(item_id)
        ks = info_font.render(f"类型: {kind}", True, (180, 175, 200))
        surface.blit(ks, (dx + 16, dy + 66))

        # 持有数量
        held, max_stack = self._get_item_held(item_id)
        hs = info_font.render(f"持有: {held} / {max_stack}", True,
                              (200, 195, 210) if held < max_stack else (240, 140, 140))
        surface.blit(hs, (dx + 16, dy + 90))

        # 描述（从物品数据库获取）
        desc = self._get_item_description(item_id)
        if desc:
            # 自动换行描述
            words = desc
            line_y = dy + 120
            for line in self._wrap_text(words, dw - 32, desc_font):
                ds = desc_font.render(line, True, (150, 145, 170))
                surface.blit(ds, (dx + 16, line_y))
                line_y += 18
                if line_y > dy + dh - 24:
                    break

        # 属性详情（武器/护甲额外展示）
        extra_lines = self._get_item_extra_lines(item_id)
        if extra_lines and extra_lines != "":
            line_y = dy + 180 if not desc else dy + 160
            for line in extra_lines.split(" | "):
                es = desc_font.render(line, True, (160, 200, 220))
                surface.blit(es, (dx + 16, line_y))
                line_y += 18

    # ----------------------------------------------------------------
    # 子渲染：底部信息
    # ----------------------------------------------------------------

    def _render_bottom(self, surface: pygame.Surface, px: int, py: int) -> None:
        bottom_y = py + PANEL_H - 48
        info_font = self._font(18)
        hint_font = self._font(16)

        # 灵魂碎片数
        souls = getattr(self._player, "soul_fragments", 0) if self._player else 0
        soul_s = info_font.render(f"灵魂碎片: {souls}", True, (220, 200, 80))
        surface.blit(soul_s, (px + 24, bottom_y))

        # 操作提示
        hints = "[W/S] 选择  [Q/E] 切换分类  [Enter] 购买  [ESC] 离开"
        hint_s = hint_font.render(hints, True, (140, 135, 160))
        surface.blit(hint_s, (px + PANEL_W // 2 - hint_s.get_width() // 2, bottom_y))

        # 消息提示
        if self._message and self._msg_timer > 0:
            msg_color = COLOR_MSG_OK if "成功" in self._message else COLOR_MSG_ERR
            if "已满" in self._message or "不足" in self._message:
                msg_color = COLOR_MSG_ERR
            msg_font = self._font(18)
            msg_s = msg_font.render(self._message, True, msg_color)
            surface.blit(msg_s, (px + PANEL_W - msg_s.get_width() - 24, bottom_y))

    # ----------------------------------------------------------------
    # 购买逻辑
    # ----------------------------------------------------------------

    def _do_buy(self) -> None:
        if self._player is None:
            return

        cat = self._current_category()
        if not cat or self._item_idx >= len(cat):
            return

        item_data = cat[self._item_idx]
        item_id = item_data["item_id"]
        price = item_data["price"]
        souls = getattr(self._player, "soul_fragments", 0)

        # 检查灵魂
        if souls < price:
            self._set_message(f"灵魂不足！需要 {price}，当前 {souls}")
            return

        # 检查最大堆叠
        held, max_stack = self._get_item_held(item_id)
        if held >= max_stack:
            self._set_message(f"持有已达上限（{max_stack}）")
            return

        # 创建物品并加入背包
        from items.item_database import item_db
        from core.event_manager import event_manager

        item = item_db.create(item_id)
        if item is None:
            self._set_message(f"物品数据异常: {item_id}")
            return

        inv = getattr(self._player, "inventory", None)
        if inv is None:
            self._set_message("背包不可用")
            return

        ok, _ = inv.add(item, 1)
        if not ok:
            self._set_message("背包已满")
            return

        # 扣除灵魂
        setattr(self._player, "soul_fragments", souls - price)

        # 通知 HUD 更新
        event_manager.emit("soul_fragments_changed", {
            "amount": souls - price,
            "player": self._player,
        })

        display_name = self._get_item_display_name(item_id)
        self._set_message(f"购买成功：{display_name}（-{price}魂）")

    # ----------------------------------------------------------------
    # 查询工具
    # ----------------------------------------------------------------

    def _current_category(self) -> list:
        if not self._categories:
            return []
        idx = max(0, min(self._category_idx, len(self._categories) - 1))
        return self._categories[idx].get("items", [])

    def _get_item_display_name(self, item_id: str) -> str:
        """从数据库获取物品显示名称。"""
        from items.item_database import item_db
        item = item_db.get(item_id)
        if item is not None:
            return getattr(item, "name", item_id)
        return item_id

    def _get_item_description(self, item_id: str) -> str:
        from items.item_database import item_db
        item = item_db.get(item_id)
        if item is not None:
            return getattr(item, "description", "")
        return ""

    def _get_item_kind(self, item_id: str) -> str:
        from items.item_database import item_db
        item = item_db.get(item_id)
        if item is None:
            return "未知"
        itype = getattr(item, "item_type", None)
        if itype is None:
            return "消耗品"
        kind_map = {
            ItemType.WEAPON:     "武器",
            ItemType.ARMOR:      "护甲",
            ItemType.CONSUMABLE: "消耗品",
            ItemType.MISC:       "特殊",
        }
        return kind_map.get(itype, "消耗品")

    def _get_item_held(self, item_id: str) -> tuple[int, int]:
        """返回 (持有数量, 最大堆叠)。"""
        from items.item_database import item_db
        item = item_db.get(item_id)
        max_stack = 99
        held = 0
        if item is not None:
            max_stack = getattr(item, "max_stack", 99)
        if self._player is not None:
            inv = getattr(self._player, "inventory", None)
            if inv is not None:
                held = inv.count(item_id)
        return held, max_stack

    def _get_item_extra_lines(self, item_id: str) -> str:
        """获取物品的额外属性展示（武器攻击力、护甲防御等）。"""
        from items.item_database import item_db
        item = item_db.get(item_id)
        if item is None:
            return ""

        itype = getattr(item, "item_type", None)

        # 武器
        if itype == ItemType.WEAPON:
            ld = getattr(item, "base_light_dmg", 0)
            hd = getattr(item, "base_heavy_dmg", 0)
            elem = getattr(item, "element", "physical")
            elem_cn = {"physical": "物理", "fire": "火", "ice": "冰",
                       "lightning": "雷", "poison": "毒",
                       "arcane": "奥术", "holy": "圣", "dark": "暗"}
            return f"轻攻击: {ld} | 重攻击: {hd} | 属性: {elem_cn.get(elem, elem)}"

        # 护甲
        if itype == ItemType.ARMOR:
            df = getattr(item, "defense", 0)
            ps = getattr(item, "poise", 0.0)
            mr = getattr(item, "magic_res", 0)
            wt = getattr(item, "weight", 0.0)
            parts = [f"防御: {df}"]
            if ps > 0:
                parts.append(f"韧性: {ps:.0f}")
            if mr > 0:
                parts.append(f"魔抗: {mr}")
            parts.append(f"重量: {wt:.1f}")
            return " | ".join(parts)

        return ""

    def _set_message(self, text: str) -> None:
        self._message = text
        self._msg_timer = 2.5

    def _wrap_text(self, text: str, max_w: int, font: pygame.font.Font) -> list[str]:
        """简单按字符数换行（中文约等宽）。"""
        chars_per_line = max(1, max_w // (font.size("中")[0] or 10))
        lines = []
        while len(text) > chars_per_line:
            # 尽量在空格或标点处断行
            split = chars_per_line
            for punct in "，。；、！？":
                pos = text.rfind(punct, 0, split)
                if pos > chars_per_line // 2:
                    split = pos + 1
                    break
            lines.append(text[:split])
            text = text[split:].lstrip()
        if text:
            lines.append(text)
        return lines

    def _font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = get_font(size)
        return self._fonts[size]
