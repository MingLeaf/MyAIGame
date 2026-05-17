# =============================================================
# ui/campfire_menu.py —— 营地菜单 UI（升级 / 强化 / 休息 / 传送）
#
# 第 8.1 阶段：营地交互时弹出菜单，允许：
#   - 升级（消耗灵魂碎片，获得属性点，可分配 6 项成长属性）
#   - 武器强化（消耗灵魂碎片 + 材料）
#   - 休息（补满 HP + 消耗品，重置敌人）
#   - 离开
# =============================================================
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING, Optional

from utils.color import WHITE, UI_HIGHLIGHT, COLOR_HP
from ui.font_manager import get_font
from config import SCREEN_WIDTH, SCREEN_HEIGHT

if TYPE_CHECKING:
    from entities.player.player import Player

# 属性名中文映射 + 作用描述
ATTR_NAMES = {
    "strength":     "力量",
    "dexterity":    "敏捷",
    "intelligence": "智慧",
    "faith":        "信仰",
    "vitality":     "体魄",
    "endurance":    "耐性",
}

ATTR_DESCRIPTIONS = {
    "strength":     "重型武器伤害↑，满足重武器装备",
    "dexterity":    "轻型武器伤害↑，翻滚距离↑",
    "intelligence": "魔法伤害↑，法术消耗品效果↑",
    "faith":        "神圣伤害↑，治疗消耗品效果↑",
    "vitality":     "最大HP↑，耐力恢复速度↑",
    "endurance":    "最大耐力↑，最大负重↑",
}


class CampfireMenu:
    """
    营地菜单覆盖层。
    打开时暂停游戏，关闭后继续。
    """

    def __init__(self):
        self.visible: bool = False
        self._player: Optional["Player"] = None

        # 菜单项
        self._menu_items = [
            ("升级",     "level_up"),
            ("武器强化", "weapon_upgrade"),
            ("传送",     "teleport"),
            ("休息",     "rest"),
            ("离开",     "leave"),
        ]
        self._selected: int = 0

        # 升级子面板
        self._show_upgrade_panel: bool = False
        self._upgrade_selected: int = 0

        # 武器强化子面板
        self._show_weapon_panel: bool = False

        # 传送子面板（第 10 阶段）
        self._show_teleport_panel: bool = False
        self._teleport_targets: list = []
        self._teleport_selected: int = 0

        # 消息提示
        self._message: str = ""
        self._msg_timer: float = 0.0

    def open(self, player: "Player") -> None:
        self.visible = True
        self._player = player
        self._selected = 0
        self._show_upgrade_panel = False
        self._show_weapon_panel = False
        self._show_teleport_panel = False
        self._teleport_targets = []
        self._teleport_selected = 0
        self._message = ""
        self._msg_timer = 0.0

    def close(self) -> None:
        self.visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        处理事件。返回 True 表示事件已被消耗。
        """
        if not self.visible:
            return False

        if event.type != pygame.KEYDOWN:
            return True   # 拦截所有非键盘输入

        # ---- 升级面板输入 ----
        if self._show_upgrade_panel:
            return self._handle_upgrade_input(event)

        # ---- 武器强化面板输入 ----
        if self._show_weapon_panel:
            return self._handle_weapon_input(event)

        # ---- 传送面板输入（第 10 阶段）----
        if self._show_teleport_panel:
            return self._handle_teleport_input(event)

        # ---- 主菜单输入 ----
        if event.key == pygame.K_w or event.key == pygame.K_UP:
            self._selected = (self._selected - 1) % len(self._menu_items)
            return True
        if event.key == pygame.K_s or event.key == pygame.K_DOWN:
            self._selected = (self._selected + 1) % len(self._menu_items)
            return True
        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            return self._select_menu()
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_f:
            self.close()
            return True

        return True

    # ----------------------------------------------------------------
    # 主菜单选择
    # ----------------------------------------------------------------

    def _select_menu(self) -> bool:
        if self._player is None:
            return True
        action = self._menu_items[self._selected][1]

        if action == "level_up":
            self._show_upgrade_panel = True
            self._upgrade_selected = 0
        elif action == "weapon_upgrade":
            self._show_weapon_panel = True
        elif action == "teleport":
            self._show_teleport_panel = True
            self._load_teleport_targets()
        elif action == "rest":
            self._do_rest()
        elif action == "leave":
            self.close()

        return True

    def _do_rest(self) -> None:
        """营地休息：恢复 + 补满消耗品 + 重置全部敌人"""
        from systems.campfire_system import CampfireSystem
        from map.world_map import world_map
        # 获取当前 area
        area = None
        if hasattr(self._player, "current_area"):
            area = self._player.current_area
        if area is None:
            area = world_map.current_area

        # 1. 恢复 HP / Stamina / Mana + 补满消耗品
        CampfireSystem.rest(self._player, area=None)  # 不自动重置敌人

        # 2. 重置区域全部敌人
        if area is not None:
            area.reload()

        self._message = "已恢复全部生命/灵力/消耗品，敌人已重置"
        self._msg_timer = 2.0

    # ----------------------------------------------------------------
    # 升级面板
    # ----------------------------------------------------------------

    def _handle_upgrade_input(self, event) -> bool:
        if self._player is None:
            return True

        if event.key == pygame.K_ESCAPE:
            self._show_upgrade_panel = False
            return True

        # 属性分配
        attr_keys = [
            pygame.K_1, pygame.K_2, pygame.K_3,
            pygame.K_4, pygame.K_5, pygame.K_6,
        ]
        attr_names = list(ATTR_NAMES.keys())
        if event.key in attr_keys:
            idx = attr_keys.index(event.key)
            if idx < len(attr_names) and self._player.build.unspent > 0:
                self._player.allocate_stat(attr_names[idx], 1)
                self._message = f"{ATTR_NAMES[attr_names[idx]]} +1"
                self._msg_timer = 1.5
            return True

        # 消耗灵魂升级
        if event.key == pygame.K_RETURN:
            from systems.progression_system import ProgressionSystem
            cost = ProgressionSystem.get_level_cost(self._player.build.level + 1)
            souls = self._player.soul_fragments
            if souls >= cost:
                leveled = ProgressionSystem.spend_souls_to_level_up(self._player, 1)
                if leveled > 0:
                    self._message = f"升级至 Lv.{self._player.build.level}！获得 {leveled} 属性点"
                else:
                    self._message = "已满级"
            else:
                self._message = f"灵魂不足（需要 {cost}，当前 {souls}）"
            self._msg_timer = 2.0
            return True

        return True

    # ----------------------------------------------------------------
    # 武器强化面板
    # ----------------------------------------------------------------

    def _handle_weapon_input(self, event) -> bool:
        if self._player is None:
            return True

        if event.key == pygame.K_ESCAPE:
            self._show_weapon_panel = False
            return True

        if event.key == pygame.K_RETURN:
            from systems.upgrade_system import UpgradeSystem
            weapon = self._player.weapon
            route = getattr(weapon, "upgrade_route", "none")
            ok, msg = UpgradeSystem.upgrade_weapon(self._player, weapon, route)
            self._message = msg
            self._msg_timer = 2.0
            return True

        return True

    # ----------------------------------------------------------------
    # 更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self._msg_timer > 0:
            self._msg_timer = max(0, self._msg_timer - dt)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible or self._player is None:
            return

        p = self._player

        # ---- 子面板 ----
        if self._show_upgrade_panel:
            self._render_upgrade_panel(surface, p)
            return
        if self._show_weapon_panel:
            self._render_weapon_panel(surface, p)
            return
        if self._show_teleport_panel:
            self._render_teleport_panel(surface, p)
            return

        # ---- 半透明遮罩 ----
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        # ---- 菜单面板（居中）----
        pw, ph = 360, 380
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2

        # 背景面板
        pygame.draw.rect(surface, (25, 22, 35), (px, py, pw, ph))
        pygame.draw.rect(surface, (80, 75, 100), (px, py, pw, ph), 2)

        # 标题
        title_font = get_font(28)
        title_surf = title_font.render("营地", True, UI_HIGHLIGHT)
        surface.blit(title_surf, (px + pw // 2 - title_surf.get_width() // 2, py + 16))

        # 玩家状态
        info_font = get_font(18)
        info_lines = [
            f"Lv.{p.build.level}    灵魂碎片: {p.soul_fragments}",
            f"HP: {p.stats.hp}/{p.stats.max_hp}    Mana: {p.stats.mana}/{p.stats.max_mana}",
            f"可分配点数: {p.build.unspent}",
        ]
        for i, line in enumerate(info_lines):
            surf = info_font.render(line, True, (200, 200, 210))
            surface.blit(surf, (px + 20, py + 55 + i * 24))

        # 武器信息
        weapon = getattr(p, "weapon", None)
        if weapon is not None:
            wpn_name = getattr(weapon, "display_name", "武器")
            wpn_lv = getattr(weapon, "upgrade_level", 0)
            wpn_route = getattr(weapon, "upgrade_route", "none")
            route_cn = {"none": "", "sharp": "锋锐", "heavy": "沉重", "blessed": "加护", "elemental": "元素"}
            wpn_info = f"武器: {wpn_name} +{wpn_lv}"
            if wpn_route != "none":
                wpn_info += f" ({route_cn.get(wpn_route, wpn_route)})"
            wpn_surf = info_font.render(wpn_info, True, (220, 200, 150))
            surface.blit(wpn_surf, (px + 20, py + 128))

        # 菜单项
        menu_font = get_font(22)
        for i, (label, _) in enumerate(self._menu_items):
            y = py + 165 + i * 32
            if i == self._selected:
                # 高亮背景
                pygame.draw.rect(surface, (60, 55, 80),
                                 (px + 12, y - 2, pw - 24, 30))
                color = UI_HIGHLIGHT
                prefix = "▶ "
            else:
                color = (170, 170, 190)
                prefix = "   "
            surf = menu_font.render(f"{prefix}{label}", True, color)
            surface.blit(surf, (px + 24, y))

        # 消息提示
        if self._message and self._msg_timer > 0:
            msg_font = get_font(18)
            msg_surf = msg_font.render(self._message, True, (120, 240, 140))
            surface.blit(msg_surf, (px + 20, py + ph - 30))

    # ----------------------------------------------------------------
    # 升级面板
    # ----------------------------------------------------------------

    def _render_upgrade_panel(self, surface: pygame.Surface, p: "Player") -> None:
        from systems.progression_system import ProgressionSystem

        # 遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        pw, ph = 540, 520
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2

        pygame.draw.rect(surface, (25, 22, 35), (px, py, pw, ph))
        pygame.draw.rect(surface, (80, 75, 100), (px, py, pw, ph), 2)

        title_font = get_font(26)
        title_surf = title_font.render("升级", True, UI_HIGHLIGHT)
        surface.blit(title_surf, (px + pw // 2 - title_surf.get_width() // 2, py + 14))

        info_font = get_font(18)
        cost = ProgressionSystem.get_level_cost(p.build.level + 1)
        info_lines = [
            f"当前等级: Lv.{p.build.level}    灵魂碎片: {p.soul_fragments}",
            f"下次升级需要: {cost} 灵魂碎片",
            f"可分配点数: {p.build.unspent}",
        ]
        for i, line in enumerate(info_lines):
            surf = info_font.render(line, True, (200, 200, 210))
            surface.blit(surf, (px + 20, py + 48 + i * 22))

        # 六项属性
        attr_keys = list(ATTR_NAMES.keys())
        attr_font = get_font(18)
        desc_font = get_font(14)
        for i, key in enumerate(attr_keys):
            y = py + 130 + i * 52
            val = getattr(p.growth, key, 0)
            # 属性行背景
            row_color = (45, 40, 58) if i % 2 == 0 else (38, 34, 50)
            pygame.draw.rect(surface, row_color, (px + 12, y, pw - 24, 46))
            # 编号
            num_surf = get_font(14).render(f"[{i+1}]", True, (140, 140, 160))
            surface.blit(num_surf, (px + 18, y + 14))
            # 属性名 + 值
            attr_surf = attr_font.render(
                f"{ATTR_NAMES[key]:　<6} {val:>2}",
                True, (220, 220, 240)
            )
            surface.blit(attr_surf, (px + 50, y + 4))
            # 描述文字
            desc = ATTR_DESCRIPTIONS.get(key, "")
            desc_surf = desc_font.render(desc, True, (140, 140, 170))
            surface.blit(desc_surf, (px + 50, y + 26))
            # 加号按钮（若有可分配点）
            if p.build.unspent > 0:
                plus_surf = get_font(20).render("[+]", True, (120, 240, 120))
                surface.blit(plus_surf, (px + pw - 70, y + 12))

        # 操作提示
        hint_font = get_font(16)
        hints = [
            "按 [1~6] 分配属性点    按 [Enter] 消耗灵魂升级",
            "按 [ESC] 返回菜单",
        ]
        for i, h in enumerate(hints):
            surf = hint_font.render(h, True, (150, 150, 170))
            surface.blit(surf, (px + 20, py + ph - 50 + i * 22))

        # 消息
        if self._message and self._msg_timer > 0:
            msg_font = get_font(18)
            msg_surf = msg_font.render(self._message, True, (120, 240, 140))
            surface.blit(msg_surf, (px + pw // 2 - msg_surf.get_width() // 2, py + ph - 24))

    # ----------------------------------------------------------------
    # 武器强化面板
    # ----------------------------------------------------------------

    def _render_weapon_panel(self, surface: pygame.Surface, p: "Player") -> None:
        from systems.upgrade_system import UpgradeSystem
        weapon = getattr(p, "weapon", None)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        pw, ph = 440, 320
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2

        pygame.draw.rect(surface, (25, 22, 35), (px, py, pw, ph))
        pygame.draw.rect(surface, (80, 75, 100), (px, py, pw, ph), 2)

        title_font = get_font(26)
        title_surf = title_font.render("武器强化", True, UI_HIGHLIGHT)
        surface.blit(title_surf, (px + pw // 2 - title_surf.get_width() // 2, py + 14))

        info_font = get_font(18)
        if weapon is None:
            surf = info_font.render("没有武器可强化", True, (180, 100, 100))
            surface.blit(surf, (px + 20, py + 60))
        else:
            wpn_name = getattr(weapon, "display_name", "武器")
            wpn_lv = getattr(weapon, "upgrade_level", 0)
            preview = UpgradeSystem.preview_upgrade(p, weapon)

            lines = [
                f"当前武器: {wpn_name} +{wpn_lv}",
                f"灵魂碎片: {p.soul_fragments}",
            ]
            if "error" in preview:
                lines.append(f"状态: {preview['error']}")
            else:
                souls_cost = preview.get("souls_cost", 0)
                lines.append(f"下一级 (+{preview.get('next_level', 0)}): 需要 {souls_cost} 灵魂")
                if preview.get("mat_qty", 0) > 0:
                    mat_name = preview.get("mat_name", "材料")
                    lines.append(f"材料: {mat_name} ×{preview['mat_qty']} "
                                f"(当前持有 {preview.get('mat_have', 0)})")

            for i, line in enumerate(lines):
                surf = info_font.render(line, True, (200, 200, 210))
                surface.blit(surf, (px + 20, py + 50 + i * 24))

            # 提示
            hint_font = get_font(16)
            hint_surf = hint_font.render("按 [Enter] 强化    按 [ESC] 返回", True, (150, 150, 170))
            surface.blit(hint_surf, (px + 20, py + ph - 40))

        # 消息
        if self._message and self._msg_timer > 0:
            msg_font = get_font(18)
            color = (120, 240, 140) if "成功" in self._message else (240, 140, 140)
            msg_surf = msg_font.render(self._message, True, color)
            surface.blit(msg_surf, (px + pw // 2 - msg_surf.get_width() // 2, py + ph - 20))

    # ----------------------------------------------------------------
    # 传送面板（第 10 阶段）
    # ----------------------------------------------------------------

    def _load_teleport_targets(self):
        """从 CampfireSystem 加载可传送的营地列表，并注入友好名称。"""
        from systems.campfire_system import CampfireSystem
        self._teleport_targets = CampfireSystem.get_transport_targets(None)
        # 补充友好名称
        import json, os
        from config import DATA_DIR
        wc_path = os.path.join(DATA_DIR, "maps", "world_config.json")
        area_names = {}
        if os.path.isfile(wc_path):
            try:
                with open(wc_path, encoding="utf-8") as f:
                    wc = json.load(f)
                for a in wc.get("areas", []):
                    area_names[a["id"]] = a.get("name", a["id"])
            except Exception:
                pass
        for t in self._teleport_targets:
            t["name"] = area_names.get(t["area_id"], t.get("campfire_id", "?"))
        self._teleport_selected = 0

    def _handle_teleport_input(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            self._show_teleport_panel = False
            return True
        if event.key in (pygame.K_w, pygame.K_UP):
            if self._teleport_targets:
                self._teleport_selected = (self._teleport_selected - 1) % len(self._teleport_targets)
            return True
        if event.key in (pygame.K_s, pygame.K_DOWN):
            if self._teleport_targets:
                self._teleport_selected = (self._teleport_selected + 1) % len(self._teleport_targets)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return self._do_teleport()
        return True

    def _do_teleport(self) -> bool:
        if not self._teleport_targets or self._player is None:
            return True
        target = self._teleport_targets[self._teleport_selected]
        target_area = target.get("area_id", "")
        target_x = target.get("x", 0)
        target_y = target.get("y", 0)

        if not target_area:
            self._message = "传送失败：无效目标"
            self._msg_timer = 1.5
            return True

        # 检查目标区域地图文件存在
        import os
        from config import DATA_DIR
        map_dir = os.path.join(DATA_DIR, "maps", target_area)
        if not os.path.isdir(map_dir):
            self._message = f"地图未开放: {target_area}"
            self._msg_timer = 1.5
            return True

        # 先休息再传送
        from systems.campfire_system import CampfireSystem
        CampfireSystem.rest(self._player, area=None)

        # 更新复活营地 + 设置玩家位置
        campfire_id = target.get("campfire_id", "")
        if campfire_id:
            CampfireSystem.activate(campfire_id, target_area, target_x, target_y)

        # 关闭菜单，传送。保留当前玩家状态。
        self.visible = False
        self._show_teleport_panel = False

        from core.scene_manager import scene_manager
        from scenes.game_scene import GameScene
        scene = GameScene(area_id=target_area, restart=True,
                          _teleport_x=target_x, _teleport_y=target_y,
                          _existing_player=self._player)
        scene_manager.replace(scene)
        return True

    def _render_teleport_panel(self, surface: pygame.Surface, p: "Player") -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        pw, ph = 400, 360
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2

        pygame.draw.rect(surface, (25, 22, 35), (px, py, pw, ph))
        pygame.draw.rect(surface, (80, 75, 100), (px, py, pw, ph), 2)

        title_font = get_font(26)
        title_surf = title_font.render("营地传送", True, UI_HIGHLIGHT)
        surface.blit(title_surf, (px + pw // 2 - title_surf.get_width() // 2, py + 14))

        if not self._teleport_targets:
            info_font = get_font(18)
            surf = info_font.render("暂无已激活的营地可传送", True, (180, 180, 180))
            surface.blit(surf, (px + 20, py + 80))
        else:
            item_font = get_font(20)
            for i, t in enumerate(self._teleport_targets):
                y = py + 55 + i * 30
                cf_name = t.get("name", t.get("campfire_id", "?"))
                area = t.get("area_id", "?")
                label = f"{cf_name} ({area})"
                if i == self._teleport_selected:
                    pygame.draw.rect(surface, (60, 55, 80), (px + 12, y - 2, pw - 24, 28))
                    color = UI_HIGHLIGHT
                    prefix = "▶ "
                else:
                    color = (170, 170, 190)
                    prefix = "   "
                surf = item_font.render(f"{prefix}{label}", True, color)
                surface.blit(surf, (px + 24, y))

        hint_font = get_font(16)
        hint_surf = hint_font.render("W/S: 选择  Enter: 传送  ESC: 返回", True, (150, 150, 170))
        surface.blit(hint_surf, (px + 20, py + ph - 40))

        if self._message and self._msg_timer > 0:
            msg_font = get_font(18)
            msg_surf = msg_font.render(self._message, True, (240, 200, 120))
            surface.blit(msg_surf, (px + pw // 2 - msg_surf.get_width() // 2, py + ph - 20))
