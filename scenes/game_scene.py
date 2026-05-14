# =============================================================
# scenes/game_scene.py —— 核心游戏场景（第三阶段：玩家角色系统）
# =============================================================

from __future__ import annotations
import pygame

from scenes.base_scene  import BaseScene
from core.camera        import Camera
from core.scene_manager import scene_manager
from map.world_map      import world_map
from entities.player    import Player
from ui.hud             import HUD
from ui.inventory_screen  import InventoryScreen
from ui.equipment_screen  import EquipmentScreen
from ui.death_screen      import DeathScreen
from ui.campfire_menu     import CampfireMenu
from utils.color        import UI_HIGHLIGHT
from config             import SCREEN_WIDTH, SCREEN_HEIGHT
import utils.debug as debug
from ui.font_manager    import get_font
from combat.hit_resolver   import HitResolver
from combat.floating_text  import FloatingTextManager
from combat.drop_system    import roll_drops, apply_drops_to_player
from items.item_manager    import ItemManager
from systems.loot_system   import LootSystem
from core.event_manager    import event_manager
# 第 8 阶段：游戏规则核心系统
from systems.soul_fragment_system import SoulFragmentSystem
from systems.respawn_system       import RespawnSystem
from systems.campfire_system      import CampfireSystem
from systems.quest_system         import QuestSystem


class GameScene(BaseScene):
    """
    第三阶段游戏场景：
    - 正式 Player 类（状态机 + 数值系统）
    - HUD 血条 / 耐力条 / 灵力条
    - 摄像机跟随
    """

    def __init__(self, area_id: str = "area_graveyard", restart: bool = False):
        self._area_id  = area_id
        self._restart  = restart          # True = 重新开始，需要重载区域动态对象
        self._area     = None
        self._camera   = Camera()
        self._player: Player | None = None
        self._hud      = HUD()
        self._hint_font = None
        self._loaded   = False

        # ---- 战斗系统 ----
        self._floating_texts = FloatingTextManager()
        self._hit_resolver   = HitResolver(ftm=self._floating_texts)

        # ---- 背包 & 装备界面 ----
        self._inv_screen   = InventoryScreen()
        self._equip_screen = EquipmentScreen()

        # ---- 死亡界面（第 8.1 阶段）----
        self._death_screen = DeathScreen()
        # 死亡暂停标记：true 时暂停除死亡界面外的所有游戏逻辑
        self._death_paused: bool = False

        # ---- 营地菜单（第 8.1 阶段）----
        self._campfire_menu = CampfireMenu()
        # 营地暂停标记
        self._campfire_paused: bool = False

        # ---- Boss 触发标记 ----
        self._boss_triggered: bool = False

    def on_enter(self):
        pygame.font.init()
        self._hint_font = get_font(18)

        world_map.load_config()

        # 重新开始：强制重载区域动态对象（敌人 + 篝火全部重置）
        if self._restart:
            self._area = world_map.reload_area(self._area_id)
        else:
            self._area = world_map.enter_area(self._area_id)

        spawn_x, spawn_y = self._area.get_spawn_point()
        self._player = Player(spawn_x, spawn_y)
        # 让武器战技 / 特殊物品可访问 area.projectiles / dropped_items
        self._player.current_area = self._area

        # 第 7 阶段：发放初始装备 + 消耗品（仅本 GameScene 入口生效）
        self._player.grant_starting_kit()

        self._camera.set_bounds(self._area.world_bounds)
        self._camera.center_on(spawn_x, spawn_y)

        # 清空飘字
        self._floating_texts.clear()

        # ---- 监听敌人死亡，处理掉落 ----
        event_manager.subscribe("enemy_dead", self._on_enemy_dead)
        # ---- 监听拾取物品，弹飘字 ----
        event_manager.subscribe("item_picked_up", self._on_item_picked_up)
        # ---- 监听套装激活/解除，弹飘字 ----
        event_manager.subscribe("set_bonus_activated",   self._on_set_bonus_activated)
        event_manager.subscribe("set_bonus_deactivated", self._on_set_bonus_deactivated)
        # ---- 监听弓无箭事件，弹提示 ----
        event_manager.subscribe("weapon_no_ammo", self._on_weapon_no_ammo)

        # 第 8 阶段：初始化进度系统 + 监听灵魂碎片事件
        QuestSystem.init()
        event_manager.subscribe("soul_fragments_changed", self._on_soul_fragments_changed)
        event_manager.subscribe("death_relic_recovered",  self._on_death_relic_recovered)
        event_manager.subscribe("player_leveled_up",      self._on_player_leveled_up)
        event_manager.subscribe("consumables_refilled",   self._on_consumables_refilled)

        self._loaded = True

    def on_exit(self):
        """场景退出时取消事件订阅，防止悬空引用。"""
        event_manager.unsubscribe("enemy_dead",            self._on_enemy_dead)
        event_manager.unsubscribe("item_picked_up",        self._on_item_picked_up)
        event_manager.unsubscribe("set_bonus_activated",   self._on_set_bonus_activated)
        event_manager.unsubscribe("set_bonus_deactivated", self._on_set_bonus_deactivated)
        event_manager.unsubscribe("weapon_no_ammo",        self._on_weapon_no_ammo)
        event_manager.unsubscribe("soul_fragments_changed", self._on_soul_fragments_changed)
        event_manager.unsubscribe("death_relic_recovered",  self._on_death_relic_recovered)
        event_manager.unsubscribe("player_leveled_up",      self._on_player_leveled_up)
        event_manager.unsubscribe("consumables_refilled",   self._on_consumables_refilled)

    def on_resume(self):
        """从 BossScene pop 后恢复：重置雾门触发标记，允许再次进入。"""
        self._boss_triggered = False
        self._death_paused = False

    def _on_enemy_dead(self, data: dict) -> None:
        """
        监听 enemy_dead 事件，执行掉落逻辑 + 灵魂碎片。
        data = {"enemy": BaseEnemy 实例}

        第 7 阶段改造：
            通过 LootSystem.spawn_for_enemy 统一处理，掉落表
            优先取自全局 data/balance/loot_tables.json，未匹配
            时回退到 enemy.drop_table（向后兼容）。

        第 8 阶段改造：
            + 灵魂碎片自动入账（SoulFragmentSystem.grant_for_enemy）
        """
        if self._player is None or self._area is None:
            return
        enemy = data.get("enemy")
        if enemy is None:
            return

        # ---- 灵魂碎片（第 8 阶段）----
        souls_gained = SoulFragmentSystem.grant_for_enemy(self._player, enemy)
        if souls_gained > 0:
            wx = enemy.rect.centerx
            wy = enemy.rect.top
            self._floating_texts.add(
                f"+{souls_gained} 灵魂",
                wx, wy - 16,
                color=(180, 255, 140),
                size=15,
                lifetime=1.4,
            )

        # ---- 物品掉落 ----
        spawned = LootSystem.spawn_for_enemy(self._area, enemy)
        if spawned:
            wx = enemy.rect.centerx
            wy = enemy.rect.top
            # 飘字提示有物品掉落
            for di in spawned:
                from items.item_database import item_db
                proto = item_db.get(di.item_id)
                name  = proto.name if proto else di.item_id
                self._floating_texts.add(
                    f"掉落 {name}×{di.quantity}",
                    wx, wy - 4,
                    color=(220, 200, 120),
                    size=14,
                    lifetime=1.6,
                )

    def _on_item_picked_up(self, data: dict) -> None:
        """玩家拾取掉落物时显示飘字提示。"""
        if self._player is None:
            return
        name = data.get("name", data.get("item_id", "物品"))
        qty  = data.get("quantity", 1)
        wx   = data.get("world_x", self._player.rect.centerx)
        wy   = data.get("world_y", self._player.rect.top)
        self._floating_texts.add(
            f"获得 {name}×{qty}",
            wx, wy,
            color=(120, 240, 140),
            size=15,
            lifetime=1.8,
        )

    def _on_set_bonus_activated(self, data: dict) -> None:
        """套装效果激活 → 金色飘字 + 头顶提示。"""
        if self._player is None:
            return
        name = data.get("set_name", data.get("set_id", ""))
        wx = self._player.rect.centerx
        wy = self._player.rect.top - 12
        self._floating_texts.add(
            f"★ {name} 已激活",
            wx, wy,
            color=(255, 215, 80),
            size=18,
            lifetime=2.4,
        )

    def _on_set_bonus_deactivated(self, data: dict) -> None:
        if self._player is None:
            return
        name = data.get("set_name", data.get("set_id", ""))
        wx = self._player.rect.centerx
        wy = self._player.rect.top - 12
        self._floating_texts.add(
            f"{name} 解除",
            wx, wy,
            color=(180, 180, 200),
            size=14,
            lifetime=1.4,
        )

    def _on_weapon_no_ammo(self, data: dict) -> None:
        if self._player is None:
            return
        wx = self._player.rect.centerx
        wy = self._player.rect.top - 16
        self._floating_texts.add(
            "无箭可用",
            wx, wy,
            color=(255, 90, 90),
            size=15,
            lifetime=1.2,
        )

    # ----------------------------------------------------------------
    # 第 8 阶段：灵魂碎片 / 死亡遗物 / 升级 / 营地补满 事件处理
    # ----------------------------------------------------------------

    def _on_soul_fragments_changed(self, data: dict) -> None:
        """灵魂碎片变化时显示飘字。在敌人死亡位置 / 玩家头顶显示。"""
        if self._player is None:
            return
        amount = data.get("amount", 0)
        source = data.get("source", "")
        if amount == 0:
            return

        # 敌人掉落 → 不在此处显示（已在 _on_enemy_dead 中显示在敌人位置）
        if source == "enemy":
            return

        wx = self._player.rect.centerx
        wy = self._player.rect.top - 30
        if amount > 0:
            self._floating_texts.add(
                f"+{amount} 灵魂",
                wx, wy,
                color=(180, 255, 140),
                size=14,
                lifetime=1.2,
            )
        else:
            self._floating_texts.add(
                f"{amount} 灵魂 (遗失)",
                wx, wy,
                color=(255, 100, 100),
                size=14,
                lifetime=1.8,
            )

    def _on_death_relic_recovered(self, data: dict) -> None:
        """捡回遗物时显示大飘字。"""
        if self._player is None:
            return
        amount = data.get("amount", 0)
        wx = self._player.rect.centerx
        wy = self._player.rect.top - 20
        self._floating_texts.add(
            f"◇ 捡回 {amount} 灵魂碎片 ◇",
            wx, wy,
            color=(255, 215, 60),
            size=18,
            lifetime=2.5,
        )

    def _on_player_leveled_up(self, data: dict) -> None:
        """升级时显示飘字。"""
        if self._player is None:
            return
        levels = data.get("levels", 1)
        new_lv = data.get("new_level", 1)
        wx = self._player.rect.centerx
        wy = self._player.rect.top - 30
        self._floating_texts.add(
            f"▲ 升级至 Lv.{new_lv} ▲",
            wx, wy,
            color=(100, 220, 255),
            size=18,
            lifetime=2.2,
        )

    def _on_consumables_refilled(self, data: dict) -> None:
        """消耗品补满时显示飘字。"""
        if self._player is None:
            return
        count = data.get("count", 0)
        wx = self._player.rect.centerx
        wy = self._player.rect.top - 20
        self._floating_texts.add(
            f"● 消耗品已补满 ({count}种) ●",
            wx, wy,
            color=(255, 180, 100),
            size=15,
            lifetime=1.8,
        )

    # ----------------------------------------------------------------
    # 抛射物（弓箭 / 魔法弹 / 毒飞镖）每帧更新
    # ----------------------------------------------------------------

    def _update_projectiles(self, dt: float) -> None:
        if self._area is None:
            return
        projs = getattr(self._area, "projectiles", None)
        if not projs:
            return

        col = self._area.collision

        # 玩家发射 → 命中目标候选 = 敌人；敌人发射 → 命中目标 = 玩家
        # owner 为 self.player（含子类）的弹是玩家方
        # 注意：projectile.update 内部已通过 owner != target 过滤
        for p in list(projs):
            if not p.alive:
                continue
            owner = getattr(p, "owner", None)
            if owner is self._player:
                targets = self._area.enemies
            else:
                # 默认认为是敌方弹，命中玩家
                targets = [self._player]
            p.update(dt, col, targets)

        # 清理已死亡抛射物
        self._area.projectiles = [p for p in projs if p.alive]

    def handle_events(self, events: list):
        for event in events:
            # ---- 死亡界面优先消耗所有事件 ----
            if self._death_screen.visible:
                action = self._death_screen.handle_event(event)
                if action == "respawn":
                    # 从最近营地复活
                    RespawnSystem.handle_death(self._player, self._area)
                    self._death_screen.hide()
                    self._death_paused = False
                    continue
                elif action == "quit":
                    # 回到主菜单（同时复活，避免存档异常）
                    RespawnSystem.handle_death(self._player, self._area)
                    self._death_screen.hide()
                    self._death_paused = False
                    from scenes.main_menu_scene import MainMenuScene
                    scene_manager.switch(MainMenuScene())
                    continue
                # 其他按键被死亡界面拦截
                if event.type == pygame.KEYDOWN:
                    continue

            # ---- 营地菜单优先消耗事件 ----
            if self._campfire_menu.visible:
                if self._campfire_menu.handle_event(event):
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
                if event.key == pygame.K_f and self._player and not self._campfire_menu.visible:
                    # 优先检测：是否靠近营地
                    near_campfire = False
                    for cf in self._area.campfires:
                        if cf.try_activate(self._player.rect,
                                           player=self._player,
                                           area=self._area):
                            near_campfire = True
                    # 打开营地菜单
                    if near_campfire:
                        self._campfire_menu.open(self._player)
                        self._campfire_paused = True
                    # 其次检测：是否靠近雾门（按键交互，避免碰撞误触发）
                    elif not self._boss_triggered:
                        for br in self._area.boss_rooms:
                            if br.try_interact(self._player.rect):
                                self._boss_triggered = True
                                # 确保复活点
                                from systems.campfire_system import CampfireSystem
                                last_cf = CampfireSystem.get_last_campfire()
                                if last_cf is None and self._area.campfires:
                                    player_cx = self._player.rect.centerx
                                    nearest = min(self._area.campfires,
                                                  key=lambda cf: abs(cf.x - player_cx))
                                    area_id = getattr(self._area, "area_id", "area_graveyard")
                                    CampfireSystem.activate(nearest.campfire_id, area_id, nearest.x, nearest.y)
                                self._enter_boss_room(br)
                                continue
                # I 键：背包
                if event.key == pygame.K_i and self._player:
                    self._inv_screen.toggle(self._player)
                    if self._inv_screen.is_open:
                        self._equip_screen.close()
                # C 键：装备界面（Character）
                if event.key == pygame.K_c and self._player:
                    self._equip_screen.toggle(self._player)
                    if self._equip_screen.is_open:
                        self._inv_screen.close()
                # 调试：T 键测试受击
                if event.key == pygame.K_t and self._player:
                    self._player.take_damage(15, knockback_dir=-1)

    def update(self, dt: float):
        if not self._loaded or not self._player:
            return

        # ---- 死亡界面：暂停游戏逻辑，仅更新死亡界面 ----
        if self._death_paused:
            self._death_screen.update(dt)
            return

        # ---- 营地菜单：暂停游戏逻辑 ----
        if self._campfire_menu.visible:
            self._campfire_menu.update(dt)
            return

        # ---- 背包/装备界面打开时暂停游戏逻辑 ----
        if self._inv_screen.is_open or self._equip_screen.is_open:
            return

        self._player.update(dt, self._area.collision)

        # ---- 第 8.1 阶段：玩家死亡检测 → 显示死亡界面 ----
        # 条件：HP <= 0 且不在死亡界面暂停中
        if self._player.stats.is_dead and not self._death_paused:
            # 进入 Dead 状态（由 PlayerCombat 延迟到这里）
            if not self._player.fsm.is_in("Dead"):
                self._player.fsm.change_state("Dead")

            lost_souls = self._player.soul_fragments
            dx = self._player.rect.centerx
            dy = self._player.rect.centery

            # 先创建遗物（在死亡位置）
            if self._area is not None:
                SoulFragmentSystem.create_death_relic(self._player, self._area)

            # 显示死亡界面
            self._death_screen.show(lost_souls, dx, dy)
            self._death_paused = True
            return

        self._area.update(dt, self._player.rect)

        # ---- 第 9 阶段：雾门更新（仅更新粒子 + 检测接近，不自动触发传送）----
        if not self._boss_triggered:
            for br in self._area.boss_rooms:
                br.update(dt, self._player.rect)

        # ---- 第 8 阶段：死亡遗物更新 ----
        if self._area.death_relic is not None:
            self._area.death_relic.update(dt)
            # 每帧检测玩家是否捡回遗物
            SoulFragmentSystem.try_pickup_relic(self._player, self._area)

        self._camera.update(dt, self._player.rect)
        self._hud.update(self._player, dt)

        # ---- 敌人更新 ----
        living = []
        for enemy in self._area.enemies:
            enemy.player = self._player
            # 确保飘字管理器已绑定
            if enemy.status._ftm is None:
                enemy.status.bind_floating_text_manager(self._floating_texts)
            enemy.update(dt, self._area.collision)
            if not enemy.dead:
                living.append(enemy)
        self._area.enemies = living

        # ---- 玩家攻击框 → 敌人碰撞检测（HitResolver 接管）----
        self._hit_resolver.update(self._player, self._area.enemies)

        # ---- 抛射物更新 + 命中（玩家弓 / 敌人弓箭手 / 法师 / 毒飞镖）----
        self._update_projectiles(dt)

        # ---- 地面掉落物物理 + 自动拾取（第 6 阶段）----
        ItemManager.update_drops(self._area, dt)
        ItemManager.try_pickup_all(self._player, self._area)

        self._floating_texts.update(dt)

        if debug.enabled:
            p = self._player
            g = p.growth
            debug.add_line(f"Pos:   ({p.x:.0f}, {p.y:.0f})")
            debug.add_line(f"Vel:   ({p.vel_x:.0f}, {p.gravity.vel_y:.0f})")
            debug.add_line(f"State: {p.current_state}")
            debug.add_line(f"HP:    {p.stats.hp}/{p.stats.max_hp}")
            debug.add_line(f"STA:   {p.stats.stamina:.0f}/{p.stats.max_stamina:.0f}")
            debug.add_line(f"Inv:   {p.invincible}")
            debug.add_line(f"STR:{g.strength} DEX:{g.dexterity} VIT:{g.vitality} END:{g.endurance}")
            debug.add_line(f"Load:  {g.equip_weight:.1f}/{g.max_equip_load:.1f}kg  Roll:{g.roll_type}")
            debug.add_line(f"Souls: {p.soul_fragments}  Lv.{p.build.level}  Unspent:{p.build.unspent}")
            debug.add_line(f"Enemies: {len(self._area.enemies)}")

    def render(self, renderer):
        if not self._loaded:
            return

        surface    = renderer.screen
        cam_offset = self._camera.apply_offset()

        # 1. 背景
        surface.fill((28, 22, 35))

        # 2. 地图（背景层 + 地面层）
        self._area.render_background(renderer, self._camera)

        # 3. 区域对象（篝火等）
        self._area.render_objects(surface, cam_offset)

        # 4. 敌人
        for enemy in self._area.enemies:
            enemy.render(surface, cam_offset)

        # 4.5 抛射物
        for p in getattr(self._area, "projectiles", []):
            p.render(surface, cam_offset)

        # 5. 玩家
        if self._player:
            self._player.render(surface, cam_offset)

        # 6. 前景遮挡层
        self._area.render_foreground(renderer, self._camera)

        # 7. HUD
        if self._player:
            self._hud.render(surface, self._player)

        # 8. 伤害飘字（覆盖在 HUD 之上）
        self._floating_texts.render(surface, cam_offset)

        # 9. 操作提示（底部）
        self._render_hints(surface)

        # 10. 背包界面（覆盖层）
        self._inv_screen.render(surface)

        # 11. 装备界面（覆盖层）
        self._equip_screen.render(surface)

        # 12. 死亡界面（最高覆盖层，第 8.1 阶段）
        if self._death_screen.visible:
            self._death_screen.render(surface)

        # 13. 营地菜单（最高覆盖层，第 8.1 阶段）
        if self._campfire_menu.visible:
            self._campfire_menu.render(surface)

        pygame.display.flip()

    def _render_hints(self, surface: pygame.Surface):
        hints = [
            "A/D: 移动    Space: 跳跃    S+Space: 下穿平台",
            "Shift: 翻滚    J: 轻攻击    K: 重攻击    L: 格挡/弹反    U: 战技",
            "F: 篝火    I: 背包    C: 装备    T: 受击测试    F3: 调试    ESC: 暂停",
        ]
        font = self._hint_font
        # 右上角，从上往下排，留 12px 右边距和顶边距
        top = 12
        for text in hints:
            surf = font.render(text, True, (150, 150, 170))
            x = SCREEN_WIDTH - surf.get_width() - 12
            surface.blit(surf, (x, top))
            top += surf.get_height() + 4

    # ----------------------------------------------------------------
    # Boss 房间入口（第 9 阶段）
    # ----------------------------------------------------------------

    def _enter_boss_room(self, boss_room) -> None:
        """玩家走入雾门 → 创建 Boss 实例 + replace 到 BossScene。"""
        from scenes.boss_scene import BossScene
        from core.scene_manager import scene_manager

        # 创建 Boss 实例
        boss_cls = boss_room.boss_cls
        boss = boss_cls(boss_room.spawn_x, boss_room.spawn_y)
        boss.player = self._player

        # 切换到 Boss 场景（独立地图，push 叠加）
        boss_scene = BossScene(
            boss=boss,
            player=self._player,
            area=self._area,          # 复活源区域
            boss_room_id=boss_room.room_id,
        )
        scene_manager.push(boss_scene)
