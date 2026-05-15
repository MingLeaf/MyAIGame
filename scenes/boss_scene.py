# =============================================================
# scenes/boss_scene.py —— Boss 战斗专用场景（独立地图版）
#
# 第 9 阶段 v3：使用独立地图 data/maps/boss_duke/ 的封闭场景。
#
# 特点：
#   - 独立地图（data/maps/boss_duke/tilemap.json），40×22 封闭空间
#   - 雾门入口 → Boss 房间（col 5 出生）
#   - Boss 死亡后 col 37 出口通道亮起 → 通往 area_swamp
#   - 玩家死亡 → 营地复活 → pop 回 GameScene
#
# 第 9 阶段 v3.1 修复：
#   - Boss 位置修正（rect.bottom 直接对齐地面 row 17）
#   - 集成背包/装备界面（InventoryScreen / EquipmentScreen）
#   - 增加 I/C 按键绑定 + 暂停时跳过游戏逻辑
# =============================================================
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

from scenes.base_scene import BaseScene
from core.camera import Camera
from core.event_manager import event_manager
from core.scene_manager import scene_manager
from core.input_handler import input_handler
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from ui.hud import HUD
from ui.inventory_screen import InventoryScreen
from ui.equipment_screen import EquipmentScreen
from ui.font_manager import get_font
from combat.floating_text import FloatingTextManager
from combat.hit_resolver import HitResolver
from map.area import Area
from items.item_manager import ItemManager

if TYPE_CHECKING:
    from entities.enemy.bosses.base_boss import BaseBoss
    from entities.player.player import Player


class BossScene(BaseScene):
    """
    Boss 战独立场景。使用独立 Boss 房间地图。

    雾门 → clear_and_push BossScene
    Boss 死亡 → 出口通道亮起 → 玩家走到通道 → pop 回 GameScene
    玩家死亡 → 死亡界面 → 营地复活 → pop 回 GameScene
    """

    def __init__(self, boss: "BaseBoss", player: "Player",
                 area: "Area", boss_room_id: str = ""):
        self._boss = boss
        self._player = player
        self._source_area = area
        self._room_id = boss_room_id
        self._finished = False

        # 加载独立 Boss 地图
        self._area = Area("boss_duke")
        self._area.load()

        # 摄像机
        self._camera = Camera()
        # Boss 房间地图恰好是 40×22 瓦片 = 1280×704，屏幕 1280×720
        # 设置相机边界并居中
        self._camera.set_bounds(self._area.world_bounds)
        self._camera.center_on(
            self._area.tile_map.world_width // 2,
            self._area.tile_map.world_height // 2,
        )

        # HUD + 飘字
        self._hud = HUD()
        self._floating_texts = FloatingTextManager()
        self._hit_resolver = HitResolver(ftm=self._floating_texts)

        # ---- 背包 & 装备界面 ----
        self._inv_screen = InventoryScreen()
        self._equip_screen = EquipmentScreen()

        # Boss 血条
        from ui.boss_healthbar import BossHealthBar
        self._health_bar = BossHealthBar()

        # 死亡界面
        from ui.death_screen import DeathScreen
        self._death_screen = DeathScreen()
        self._death_paused: bool = False

        # 出口通道
        self._exit_open: bool = False
        self._exit_rect: pygame.Rect | None = None
        for t in self._area.transitions:
            self._exit_rect = t.rect

        # 状态
        self._boss_dead: bool = False
        self._finish_timer: float = 0.0

        # 将玩家 + Boss 放入 Boss 地图
        spawn = self._area.get_spawn_point()
        self._player.set_position(spawn[0], spawn[1])
        # 玩家脚底对齐地面 row 17
        self._player.rect.centerx = int(spawn[0])
        self._player.y = float(17 * self._area.tile_map.tile_size)
        
        # !!关键!! 设置玩家的当前区域为 Boss 房间，使消耗品/战技可正确生成抛射物
        self._player.current_area = self._area

        # Boss 出生在房间中央，脚底对齐地面
        tile_size = self._area.tile_map.tile_size
        ground_y = 17 * tile_size  # row 17 地面表面
        boss_spawn_x = self._area.tile_map.world_width // 2
        self._boss.x = float(boss_spawn_x)
        self._boss.y = float(ground_y)
        self._boss.player = self._player
        self._boss._current_area = self._area   # Boss 需要 area 引用统计小兵

        # 将 Boss 添加到地图敌人列表
        self._area.enemies.append(self._boss)

    def on_enter(self) -> None:
        self._health_bar.attach(self._boss)
        event_manager.subscribe("boss_killed", self._on_boss_killed)
        event_manager.subscribe("boss_revive_begin", self._on_revive_begin)
        event_manager.subscribe("boss_revived", self._on_revived)
        event_manager.subscribe("boss_summon_minions", self._on_boss_summon)
        event_manager.subscribe("summon_ally", self._on_summon_ally)
        event_manager.subscribe("enemy_dead", self._on_enemy_dead)
        event_manager.subscribe("player_buff_applied", self._on_player_buff)

    def on_exit(self) -> None:
        self._health_bar.detach()
        event_manager.unsubscribe("boss_killed", self._on_boss_killed)
        event_manager.unsubscribe("boss_revive_begin", self._on_revive_begin)
        event_manager.unsubscribe("boss_revived", self._on_revived)
        event_manager.unsubscribe("boss_summon_minions", self._on_boss_summon)
        event_manager.unsubscribe("summon_ally", self._on_summon_ally)
        event_manager.unsubscribe("enemy_dead", self._on_enemy_dead)
        event_manager.unsubscribe("player_buff_applied", self._on_player_buff)

    def update(self, dt: float) -> None:
        if self._finished:
            return

        # 死亡界面
        if self._death_paused:
            self._death_screen.update(dt)
            return

        # 背包/装备界面打开时暂停游戏逻辑
        if self._inv_screen.is_open or self._equip_screen.is_open:
            return

        col = self._area.collision

        # 玩家死亡检测
        if self._player.stats.is_dead and not self._death_paused:
            if not self._player.fsm.is_in("Dead"):
                self._player.fsm.change_state("Dead")
            lost_souls = self._player.soul_fragments
            from systems.soul_fragment_system import SoulFragmentSystem
            SoulFragmentSystem.create_death_relic(self._player, self._area)
            self._death_screen.show(lost_souls,
                                   self._player.rect.centerx,
                                   self._player.rect.centery)
            self._death_paused = True
            return

        self._health_bar.update(dt)

        # 玩家更新（无论 Boss 死活都应允许玩家移动）
        if col is not None:
            self._player.update(dt, col)

        # Boss 更新
        if self._boss_dead:
            self._finish_timer -= dt
            if self._finish_timer <= 0.0:
                self._finish_boss()
            # 检测玩家是否走到出口
            if self._exit_open and self._exit_rect and self._player:
                if self._exit_rect.colliderect(self._player.rect):
                    self._finish_boss()
        else:
            if not self._boss.dead:
                self._boss.update(dt, col)

            # ---- 更新 Boss 召唤的小兵（AI + 物理）----
            living_minions = []
            for enemy in list(self._area.enemies):
                if enemy is self._boss or enemy.dead:
                    if enemy is not self._boss and enemy.dead:
                        continue  # 死亡的召唤物移除
                    if enemy is not self._boss:
                        living_minions.append(enemy)
                    continue
                if enemy.status._ftm is None:
                    enemy.status.bind_floating_text_manager(self._floating_texts)
                # 让敌方小兵可以攻击玩家 + 友方召唤物
                enemy.attack_targets = [self._player] + getattr(self._area, "allies", [])
                enemy.update(dt, col)
                living_minions.append(enemy)
            # 保留 Boss + 存活小兵
            self._area.enemies = [e for e in self._area.enemies if e is self._boss] + living_minions

            # 玩家攻击 → Boss + 全部敌人
            self._hit_resolver.update(self._player, [self._boss] + self._area.enemies)

        # ---- 抛射物更新（毒飞镖/弓箭/魔法弹等）----
        self._update_projectiles(dt)

        # ---- 地面掉落物物理 + 自动拾取 ----
        ItemManager.update_drops(self._area, dt)
        ItemManager.try_pickup_all(self._player, self._area)

        # ---- 友方召唤物更新 ----
        for ally in getattr(self._area, "allies", []):
            if ally.dead:
                continue
            if ally.status._ftm is None:
                ally.status.bind_floating_text_manager(self._floating_texts)
            ally.update(dt, col)
        living_allies = [a for a in getattr(self._area, "allies", []) if not a.dead]
        self._area.allies = living_allies

        # 飘字 + 摄像机 + HUD
        self._floating_texts.update(dt)
        self._camera.update(dt, self._player.rect)
        self._hud.update(self._player, dt)

    def _update_projectiles(self, dt: float) -> None:
        """更新 Boss 房间内的所有抛射物（毒飞镖/弓箭/魔法弹等）。"""
        projs = getattr(self._area, "projectiles", None)
        if not projs:
            return

        col = self._area.collision
        for p in list(projs):
            if not p.alive:
                continue
            owner = getattr(p, "owner", None)
            if owner is self._player:
                targets = [self._boss]
            else:
                targets = [self._player]
            p.update(dt, col, targets)

        self._area.projectiles = [p for p in projs if p.alive]

    def handle_events(self, events: list) -> None:
        for event in events:
            if self._death_screen.visible:
                action = self._death_screen.handle_event(event)
                if action == "respawn":
                    self._do_respawn()
                    return
                elif action == "quit":
                    self._do_respawn()
                    from scenes.main_menu_scene import MainMenuScene
                    scene_manager.clear_and_push(MainMenuScene())
                    return
                if event.type == pygame.KEYDOWN:
                    continue

            # ---- 背包界面优先消耗事件 ----
            if self._inv_screen.is_open:
                if self._inv_screen.handle_event(event):
                    continue
            # ---- 装备界面优先消耗事件 ----
            if self._equip_screen.is_open:
                if self._equip_screen.handle_event(event):
                    continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from scenes.pause_scene import PauseScene
                    scene_manager.push(PauseScene())
                # I 键：背包
                if event.key == pygame.K_i and self._player:
                    self._inv_screen.toggle(self._player)
                    if self._inv_screen.is_open:
                        self._equip_screen.close()
                # C 键：装备界面
                if event.key == pygame.K_c and self._player:
                    self._equip_screen.toggle(self._player)
                    if self._equip_screen.is_open:
                        self._inv_screen.close()
                # 调试：T 键测试受击
                if event.key == pygame.K_t and self._player:
                    self._player.take_damage(15, knockback_dir=-1)

    def _do_respawn(self) -> None:
        from systems.respawn_system import RespawnSystem
        RespawnSystem.handle_death(self._player, self._source_area)
        self._death_screen.hide()
        self._death_paused = False
        self._finished = True
        scene_manager.pop()

    def render(self, renderer) -> None:
        surface = renderer.screen
        cam_offset = self._camera.apply_offset()

        surface.fill((20, 16, 28))

        # 地图
        self._area.render_background(renderer, self._camera)

        # 出口通道（Boss死亡后亮起）
        if self._exit_open and self._exit_rect:
            ex = self._exit_rect.x - cam_offset[0]
            ey = self._exit_rect.y - cam_offset[1]
            ew, eh = self._exit_rect.width, self._exit_rect.height
            # 通道高亮
            glow = pygame.Surface((ew, eh), pygame.SRCALPHA)
            glow.fill((100, 200, 255, 100))
            surface.blit(glow, (ex, ey))
            pygame.draw.rect(surface, (120, 220, 255), (ex, ey, ew, eh), 2)
            # 提示文字
            hint_font = get_font(16)
            hint = hint_font.render("离开", True, (180, 240, 255))
            surface.blit(hint, hint.get_rect(center=(ex + ew // 2, ey - 16)))

        # Boss
        if not self._boss.dead or self._boss._revive_pending:
            self._boss.render(surface, cam_offset)

        # Boss 召唤物（敌人阵营）
        for enemy in self._area.enemies:
            if enemy is not self._boss:
                enemy.render(surface, cam_offset)

        # 友方召唤物（玩家阵营）
        for ally in getattr(self._area, "allies", []):
            ally.render(surface, cam_offset)

        # 抛射物
        for p in getattr(self._area, "projectiles", []):
            p.render(surface, cam_offset)

        # 玩家
        if self._player and not self._death_paused:
            self._player.render(surface, cam_offset)

        # 前景
        self._area.render_foreground(renderer, self._camera)

        # HUD + Boss 血条 + 飘字
        if self._player:
            self._hud.render(surface, self._player)
        self._health_bar.render(surface)
        self._floating_texts.render(surface, cam_offset)

        # 背包界面（覆盖层）
        self._inv_screen.render(surface)
        # 装备界面（覆盖层）
        self._equip_screen.render(surface)

        if self._death_screen.visible:
            self._death_screen.render(surface)

    # ----------------------------------------------------------------

    def _on_boss_killed(self, data: dict) -> None:
        boss = data.get("boss")
        if boss is not self._boss:
            return
        self._boss_dead = True
        self._exit_open = True  # 打开出口通道
        self._finish_timer = 999  # 不自动结束，等玩家走到出口

    def _on_revive_begin(self, data: dict) -> None:
        pass

    def _on_revived(self, data: dict) -> None:
        self._boss_dead = False
        self._exit_open = False

    def _on_enemy_dead(self, data: dict) -> None:
        """敌人死亡 → 通知 Boss（用于召唤冷却管理）。"""
        enemy = data.get("enemy")
        if enemy is None or enemy is self._boss:
            return
        # 通知 Boss 小兵死亡
        if hasattr(self._boss, "on_minion_died"):
            self._boss.on_minion_died()

    def _on_boss_summon(self, data: dict) -> None:
        """Boss 召唤技能 → 在 Boss 房间内生成骷髅兵。"""
        boss = data.get("boss")
        if boss is not self._boss:
            return
        count = int(data.get("count", 2))
        spawn_x = float(data.get("x", self._boss.rect.centerx))
        spawn_y = float(data.get("y", self._boss.rect.bottom - 32))

        from entities.enemy.types import create_enemy

        for i in range(count):
            # 在 Boss 左右随机偏移位置生成
            offset_x = -60 + i * 80 + (0 if count <= 1 else 40)
            ex = spawn_x + offset_x
            ey = spawn_y - 32

            minion = create_enemy("undead", ex, ey)
            # 标记为 Boss 召唤物，与 Boss 同阵营
            minion.team = "enemy"
            # 绑定玩家引用（让骷髅攻击玩家）
            minion.player = self._player
            # 绑定漂浮文字
            minion.status.bind_floating_text_manager(self._floating_texts)
            # 加入 Boss 房间
            self._area.enemies.append(minion)

    def _on_summon_ally(self, data: dict) -> None:
        """骷髅骨灰 → 在 Boss 房间生成友方骷髅。"""
        ally_id = data.get("ally_id", "skeleton")
        spawn_x = float(data.get("x", 0))
        spawn_y = float(data.get("y", 0))

        from entities.enemy.types import create_enemy
        ally = create_enemy("undead", spawn_x, spawn_y - 32)
        ally.team = "player"
        # 攻击目标 = Boss + Boss 召唤物
        ally.attack_targets = [self._boss] + self._area.enemies
        ally.status.bind_floating_text_manager(self._floating_texts)
        self._area.allies.append(ally)

        self._floating_texts.add(
            "● 召唤骷髅 ●",
            spawn_x, spawn_y - 48,
            color=(180, 220, 255),
            size=16,
            lifetime=1.5,
        )

    def _on_player_buff(self, data: dict) -> None:
        """消耗品增益生效。"""
        if self._player is None:
            return
        buff_type = data.get("buff_type", "")
        value = float(data.get("value", 0))
        duration = float(data.get("duration", 30))
        self._player.stats.apply_buff(buff_type, value, duration)

        name_map = {
            "atk_bonus": "攻击力", "def_bonus": "防御力",
            "weapon_fire": "火焰附魔", "weapon_holy": "神圣附魔",
        }
        label = name_map.get(buff_type, buff_type)
        self._floating_texts.add(
            f"▲ {label} +{int(value*100)}%",
            self._player.rect.centerx, self._player.rect.top - 30,
            color=(255, 200, 80), size=14, lifetime=2.0,
        )

    def _finish_boss(self) -> None:
        self._finished = True

        boss_data = getattr(self._boss, "_boss_data", {})
        boss_id = boss_data.get("id", "")
        soul_cfg = boss_data.get("boss_soul", {})
        soul_value = soul_cfg.get("soul_value", 5000)

        from items.special.boss_soul import BossSoul
        soul = BossSoul(
            item_id=soul_cfg.get("item_id", "boss_soul_duke"),
            name=soul_cfg.get("name", "Boss 之魂"),
            description=f"击败{boss_data.get('display_name', 'Boss')}后获得的灵核。",
            boss_id=boss_id,
            soul_value=soul_value,
        )
        inv = getattr(self._player, "inventory", None)
        if inv is not None:
            inv.add(soul, 1)

        self._player.soul_fragments += soul_value
        event_manager.emit("soul_fragments_changed", {
            "amount": soul_value,
            "total": self._player.soul_fragments,
            "source": "boss_kill",
        })

        from systems.quest_system import QuestSystem
        QuestSystem.record_boss_kill(boss_id)

        event_manager.emit("boss_scene_finished", {
            "boss_id": boss_id,
            "soul_value": soul_value,
        })

        # 回到上一场景
        scene_manager.pop()


__all__ = ["BossScene"]
