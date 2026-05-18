# =============================================================
# scenes/game_scene.py —— 核心游戏场景（第三阶段：玩家角色系统）
# =============================================================

from __future__ import annotations
import pygame, logging

_log = logging.getLogger("dialogue")

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
from ui.dialogue_box      import DialogueBox
from core.dialogue_engine import DialogueEngine
from ui.shop_screen       import ShopScreen
from ui.notification      import NotificationManager
from ui.status_panel      import StatusPanel
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
# 第 11 阶段：粒子特效与音频
from animation.particle_system import ParticleManager
from audio.audio_manager import AudioManager


# Q 键快速使用消耗品优先级（从高到低）
_QUICK_USE_PRIORITY = [
    "heal_potion_small",    # 草药汤
    "heal_potion_large",    # 高级圣水
    "mana_potion_basic",    # 灵力药剂
    "antidote_universal",   # 万能解药
    "stamina_potion_basic", # 精力饮剂
    "buff_sharp_powder",    # 锋刃石粉
    "buff_iron_skin",       # 铁皮膏
    "buff_holy_oil",        # 圣油
    "buff_flame_resin",     # 烈焰松脂
    "buff_berserk",         # 狂战药
    "curse_remover_charm",  # 诅咒解符
    "skeleton_ashes",       # 骷髅骨灰
    "teleport_stone",       # 传送石
    "trap_bomb",            # 陷阱炸弹
    "poison_dart",          # 毒飞镖
]


class GameScene(BaseScene):
    """
    第三阶段游戏场景：
    - 正式 Player 类（状态机 + 数值系统）
    - HUD 血条 / 耐力条 / 灵力条
    - 摄像机跟随
    """

    def __init__(self, area_id: str = "area_graveyard", restart: bool = False,
                 *, _teleport_x: float = None, _teleport_y: float = None,
                 _existing_player = None):
        self._area_id  = area_id
        self._restart  = restart          # True = 重新开始，需要重载区域动态对象
        self._teleport_spawn = None       # 传送目标坐标 (x, y)，若设则忽略默认出生点
        if _teleport_x is not None and _teleport_y is not None:
            self._teleport_spawn = (_teleport_x, _teleport_y)
        self._existing_player = _existing_player  # 传送时保留的玩家引用
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

        # ---- 第 11 阶段·粒子特效与音频 ----
        self._particle_mgr = ParticleManager()
        self._audio_mgr = AudioManager()

        # ---- 第 10 阶段·NPC 与对话系统 ----
        self._dialogue_box = DialogueBox()
        self._dialogue_engine: "DialogueEngine" | None = None
        # 对话暂停标记
        self._dialogue_paused: bool = False

        # ---- 第 11 阶段扩展·商店界面 ----
        self._shop_screen = ShopScreen()

        # ---- 第 12 阶段·通知系统 ----
        self._notifications = NotificationManager()

        # ---- 第 12 阶段·人物属性面板（Tab 键）----
        self._status_panel = StatusPanel()

    def on_enter(self):
        pygame.font.init()
        self._hint_font = get_font(18)

        world_map.load_config()

        # 重新开始：强制重载区域动态对象（敌人 + 篝火全部重置）
        if self._restart:
            self._area = world_map.reload_area(self._area_id)
        else:
            self._area = world_map.enter_area(self._area_id)

        # 传送坐标优先于默认出生点
        if self._teleport_spawn:
            spawn_x, spawn_y = self._teleport_spawn
        else:
            spawn_x, spawn_y = self._area.get_spawn_point()

        # 传送时复用已有玩家，仅重新定位；否则创建新玩家
        if self._existing_player is not None:
            self._player = self._existing_player
            self._player.set_position(spawn_x, spawn_y)
        else:
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
        event_manager.subscribe("summon_ally",           self._on_summon_ally)
        event_manager.subscribe("player_buff_applied",   self._on_player_buff)

        # ---- 第 12 阶段修复：传送石 + 陷阱炸弹事件 ----
        event_manager.subscribe("teleport_to_campfire", self._on_teleport_to_campfire)
        event_manager.subscribe("place_trap",           self._on_place_trap)

        # ---- 第 10 阶段·NPC 事件 ----
        event_manager.subscribe("npc_open_level_up",       self._on_npc_open_level_up)
        event_manager.subscribe("npc_open_teleport",       self._on_npc_open_teleport)
        event_manager.subscribe("npc_open_weapon_upgrade", self._on_npc_open_weapon_upgrade)
        event_manager.subscribe("npc_open_shop",           self._on_npc_open_shop)
        event_manager.subscribe("dialogue_closed",          self._on_dialogue_closed)

        # ---- 第 11 阶段：音频系统初始化 ----
        self._audio_mgr.initialize()
        # 播放区域 BGM
        bgm_id = getattr(self._area, "bgm_id", self._area_id)
        self._audio_mgr.play_bgm(bgm_id)

        # ---- 第 11 阶段：粒子特效事件订阅 ----
        event_manager.subscribe("player_hurt",     self._on_particle_hurt)
        event_manager.subscribe("player_block_hit", self._on_particle_block)
        event_manager.subscribe("player_parry",    self._on_particle_parry)
        event_manager.subscribe("player_dodge",    self._on_particle_dodge)
        event_manager.subscribe("status_applied",  self._on_particle_status)
        event_manager.subscribe("weapon_art_used", self._on_particle_weapon_art)
        event_manager.subscribe("status_removed",  self._on_particle_status_removed)

        self._loaded = True

        # ---- 第 12 阶段：区域名称提示 ----
        area_name = getattr(self._area, "area_name", self._area_id)
        self._notifications.show_area(area_name)

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
        event_manager.unsubscribe("summon_ally",            self._on_summon_ally)
        event_manager.unsubscribe("player_buff_applied",    self._on_player_buff)
        event_manager.unsubscribe("teleport_to_campfire",    self._on_teleport_to_campfire)
        event_manager.unsubscribe("place_trap",              self._on_place_trap)
        event_manager.unsubscribe("npc_open_level_up",      self._on_npc_open_level_up)
        event_manager.unsubscribe("npc_open_teleport",      self._on_npc_open_teleport)
        event_manager.unsubscribe("npc_open_weapon_upgrade", self._on_npc_open_weapon_upgrade)
        event_manager.unsubscribe("npc_open_shop",           self._on_npc_open_shop)
        event_manager.unsubscribe("dialogue_closed",         self._on_dialogue_closed)

        # ---- 第 11 阶段：清理粒子 + 音频 ----
        event_manager.unsubscribe("player_hurt",     self._on_particle_hurt)
        event_manager.unsubscribe("player_block_hit", self._on_particle_block)
        event_manager.unsubscribe("player_parry",    self._on_particle_parry)
        event_manager.unsubscribe("player_dodge",    self._on_particle_dodge)
        event_manager.unsubscribe("status_applied",  self._on_particle_status)
        event_manager.unsubscribe("weapon_art_used", self._on_particle_weapon_art)
        event_manager.unsubscribe("status_removed",  self._on_particle_status_removed)
        self._particle_mgr.clear()
        self._audio_mgr.stop_bgm(fade_ms=800)

    def on_resume(self):
        """从 BossScene pop 后恢复：重置雾门触发标记 + 修复 player.current_area。"""
        self._boss_triggered = False
        self._death_paused = False
        # 第 11 阶段修复：BossScene pop 后 player.current_area 仍指向 boss_duke，
        # 必须重新指向本场景的 area。同时 BGM 切回本区域。
        if self._player is not None and self._area is not None:
            self._player.current_area = self._area
        bgm_id = getattr(self._area, "bgm_id", self._area_id)
        self._audio_mgr.play_bgm(bgm_id)

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
        # 第 12 阶段：右下角拾取通知
        self._notifications.show_item_pickup(f"获得 {name}×{qty}")

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

    def _on_player_buff(self, data: dict) -> None:
        """消耗品增益生效：应用到 PlayerStats。"""
        if self._player is None:
            return
        buff_type = data.get("buff_type", "")
        value = float(data.get("value", 0))
        duration = float(data.get("duration", 30))
        self._player.stats.apply_buff(buff_type, value, duration)

        # 飘字
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

    def _on_summon_ally(self, data: dict) -> None:
        """使用骷髅骨灰 → 生成友方骷髅兵。"""
        ally_id = data.get("ally_id", "skeleton")
        spawn_x = float(data.get("x", 0))
        spawn_y = float(data.get("y", 0))

        from entities.enemy.types import create_enemy
        # 用 undead 类型创建友方骷髅
        ally = create_enemy("undead", spawn_x, spawn_y - 32)
        ally.team = "player"
        # 将敌人列表作为攻击目标
        ally.attack_targets = self._area.enemies
        # 绑定飘字
        ally.status.bind_floating_text_manager(self._floating_texts)
        # 加入区域盟友列表
        self._area.allies.append(ally)

        # 飘字提示
        self._floating_texts.add(
            "● 召唤骷髅 ●",
            spawn_x, spawn_y - 48,
            color=(180, 220, 255),
            size=16,
            lifetime=1.5,
        )

    # ----------------------------------------------------------------
    # 第 12 阶段修复 · 传送石 → 传送回最近营地
    # ----------------------------------------------------------------

    def _on_teleport_to_campfire(self, data: dict) -> None:
        """传送石效果：传送回最近激活的营地。"""
        from systems.campfire_system import CampfireSystem
        last = CampfireSystem.get_last_campfire()
        if last is None:
            self._floating_texts.add(
                "无可用营地", self._player.rect.centerx, self._player.rect.centery,
                color=(255, 150, 60), size=16, lifetime=2.0,
            )
            return
        pos = CampfireSystem.get_position(last)
        if pos is None or self._player is None:
            return
        # 传送玩家到营地坐标
        self._player.set_position(pos["x"], pos["y"])
        self._camera.center_on(pos["x"], pos["y"])
        self._floating_texts.add(
            "● 传送成功 ●",
            pos["x"], pos["y"] - 48,
            color=(120, 220, 255),
            size=18,
            lifetime=2.0,
        )
        event_manager.emit("player_teleported", {
            "campfire_id": last,
            "x": pos["x"], "y": pos["y"],
        })

    # ----------------------------------------------------------------
    # 第 12 阶段修复 · 陷阱炸弹 → 放置定时炸弹
    # ----------------------------------------------------------------

    def _on_place_trap(self, data: dict) -> None:
        """陷阱炸弹效果：在玩家脚下放置一颗定时爆炸的炸弹。"""
        trap_x = float(data.get("x", 0))
        trap_y = float(data.get("y", 0))
        damage = int(data.get("damage", 80))

        from physics.projectile import Projectile

        # 使用 Projectile 做陷阱：速度 0，靠碰撞检测触发
        bomb = Projectile(
            x=trap_x, y=trap_y - 24,
            vx=0, vy=0,
            damage=damage,
            owner=self._player,
            element="fire",
            poise_damage=30.0,
            lifetime=10.0,      # 10 秒后自毁
            width=32,
            height=32,
            knockback=250.0,
        )
        bomb.color = (255, 100, 20)  # 橙红色，区别于普通抛射物
        if hasattr(self._area, "projectiles"):
            self._area.projectiles.append(bomb)

        self._floating_texts.add(
            "● 陷阱已放置 ●",
            trap_x, trap_y - 36,
            color=(255, 160, 40),
            size=15,
            lifetime=1.5,
        )

        # 粒子效果
        self._particle_mgr.spawn("fire_embers", position=(trap_x, trap_y - 24))

    # ----------------------------------------------------------------
    # 第 12 阶段修复 · Q 键快速使用消耗品
    # ----------------------------------------------------------------

    def _quick_use_item(self) -> None:
        """快速使用背包中的第一个消耗品（优先顺序见 _QUICK_USE_PRIORITY）。"""
        if self._player is None:
            return
        inv = self._player.inventory
        if inv is None:
            return

        # 查找可用的消耗品
        for item_id in _QUICK_USE_PRIORITY:
            for i, slot in enumerate(inv.slots):
                if slot is None or slot.item is None:
                    continue
                if getattr(slot.item, "item_id", "") == item_id:
                    ok = inv.use_item(i, self._player)
                    if ok:
                        name = getattr(slot.item, "name", item_id)
                        self._floating_texts.add(
                            f"使用 {name}",
                            self._player.rect.centerx,
                            self._player.rect.top - 10,
                            color=(200, 220, 255),
                            size=14,
                            lifetime=1.5,
                        )
                        self._notifications.show(f"使用 {name}")
                    return

    # ----------------------------------------------------------------
    # 第 10 阶段·NPC 对话事件处理
    # ----------------------------------------------------------------

    def _on_npc_open_level_up(self, data: dict) -> None:
        """守护者：打开升级面板（复用营地菜单的升级子面板）。"""
        _log.info("NPC_EVENT open_level_up player=%s", self._player is not None)
        try:
            if self._player is None:
                return
            self._campfire_menu.open(self._player)
            self._campfire_menu._show_upgrade_panel = True
            self._dialogue_box.close()
            self._dialogue_paused = False
            _log.info("NPC_EVENT open_level_up done")
        except Exception:
            import traceback
            _log.error("NPC_EVENT open_level_up FAILED:\n%s", traceback.format_exc())
            traceback.print_exc()

    def _on_npc_open_teleport(self, data: dict) -> None:
        """守护者：打开传送面板。"""
        _log.info("NPC_EVENT open_teleport")
        try:
            if self._player is None:
                return
            self._campfire_menu.open(self._player)
            self._campfire_menu._show_teleport_panel = True
            self._campfire_menu._load_teleport_targets()
            self._dialogue_box.close()
            self._dialogue_paused = False
            _log.info("NPC_EVENT open_teleport done")
        except Exception:
            import traceback
            _log.error("NPC_EVENT open_teleport FAILED:\n%s", traceback.format_exc())
            traceback.print_exc()

    def _on_npc_open_weapon_upgrade(self, data: dict) -> None:
        """铁匠：打开武器强化面板。"""
        _log.info("NPC_EVENT open_weapon_upgrade player=%s", self._player is not None)
        try:
            if self._player is None:
                return
            self._campfire_menu.open(self._player)
            self._campfire_menu._show_weapon_panel = True
            self._dialogue_box.close()
            self._dialogue_paused = False
            _log.info("NPC_EVENT open_weapon_upgrade done")
        except Exception:
            import traceback
            _log.error("NPC_EVENT open_weapon_upgrade FAILED:\n%s", traceback.format_exc())
            traceback.print_exc()

    def _on_npc_open_shop(self, data: dict) -> None:
        """商人：打开商店界面。"""
        _log.info("NPC_EVENT open_shop player=%s", self._player is not None)
        try:
            if self._player is None:
                return
            # 关闭对话
            self._dialogue_box.close()
            self._dialogue_paused = False
            # 打开商店
            self._shop_screen.open(self._player)
            _log.info("NPC_EVENT open_shop done")
        except Exception:
            import traceback
            _log.error("NPC_EVENT open_shop FAILED:\n%s", traceback.format_exc())
            traceback.print_exc()
            import traceback
            _log.error("NPC_EVENT open_shop FAILED:\n%s", traceback.format_exc())
            traceback.print_exc()

    def _on_dialogue_closed(self, data: dict) -> None:
        """对话框关闭时清除暂停标记（处理无 action 结束对话的场景）。"""
        self._dialogue_paused = False

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
        enemies = self._area.enemies

        for p in list(projs):
            if not p.alive:
                continue
            owner = getattr(p, "owner", None)
            # 玩家方抛射物（包括毒飞镖）：打敌人
            is_player_projectile = (owner is self._player)
            if is_player_projectile:
                targets = enemies
            else:
                targets = [self._player] if self._player else []
            p.update(dt, col, targets)

        alive = [p for p in projs if p.alive]
        self._area.projectiles = alive

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

            # ---- 对话框优先消耗事件（第 10 阶段）----
            if self._dialogue_box.is_open():
                if self._dialogue_box.handle_event(event):
                    continue

            # ---- 商店界面优先消耗事件（第 11 阶段）----
            if self._shop_screen.is_open:
                if self._shop_screen.handle_event(event):
                    continue

            # ---- 人物属性面板优先消耗事件（第 12 阶段·Tab 键）----
            if self._status_panel.is_open:
                if self._status_panel.handle_event(event):
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
                if event.key == pygame.K_f and self._player and not self._campfire_menu.visible and not self._dialogue_box.is_open():
                    # 优先级 1：营地篝火
                    near_campfire = False
                    for cf in self._area.campfires:
                        if cf.try_activate(self._player.rect,
                                           player=self._player,
                                           area=self._area):
                            near_campfire = True
                    if near_campfire:
                        self._campfire_menu.open(self._player)
                        self._campfire_paused = True
                    # 优先级 2：NPC 对话
                    else:
                        near_npc = None
                        for npc in self._area.npcs:
                            npc.update(0, self._player.rect)
                            if npc.is_near():
                                near_npc = npc
                                break
                        if near_npc is not None:
                            # 注入上下文
                            if hasattr(near_npc, "set_context"):
                                near_npc.set_context(self._player, self._area)
                            # 获取动作回调
                            actions = {}
                            if hasattr(near_npc, "get_actions"):
                                actions = near_npc.get_actions()
                            # 创建对话引擎
                            dia_data = near_npc.get_dialogue()
                            if dia_data:
                                self._dialogue_engine = DialogueEngine(dia_data, actions)
                                self._dialogue_engine.start()
                                name = getattr(near_npc, "display_name", "NPC")
                                self._dialogue_box.open(self._dialogue_engine, name)
                                self._dialogue_paused = True
                        # 优先级 3：雾门
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
                        self._status_panel.close()
                # Tab 键：人物属性面板（第 12 阶段）
                if event.key == pygame.K_TAB and self._player:
                    self._status_panel.toggle(self._player)
                    if self._status_panel.is_open:
                        self._inv_screen.close()
                        self._equip_screen.close()
                # 调试：T 键测试受击
                if event.key == pygame.K_t and self._player:
                    self._player.take_damage(15, knockback_dir=-1)
                # Q 键：快速使用消耗品（第 12 阶段修复）
                if event.key == pygame.K_q and self._player and not self._inv_screen.is_open:
                    self._quick_use_item()

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

        # ---- 对话进行中：暂停游戏逻辑（第 10 阶段）----
        if self._dialogue_paused:
            self._dialogue_box.update(dt)
            return

        # ---- 商店界面打开：暂停游戏逻辑（第 11 阶段）----
        if self._shop_screen.is_open:
            self._shop_screen.update(dt)
            return

        # ---- 背包/装备界面打开时暂停游戏逻辑 ----
        if self._inv_screen.is_open or self._equip_screen.is_open:
            return

        # ---- 属性面板打开时暂停游戏逻辑 ----
        if self._status_panel.is_open:
            self._status_panel.update(dt)
            return

        self._player.update(dt, self._area.collision)

        # ---- 第 10 阶段·坠落死亡检测 ----
        # 地图高度 = tile_size * height, 玩家若掉出世界底部则死亡
        world_bottom = self._area.world_bounds.bottom + 128  # 额外 128px 缓冲
        if self._player.rect.top > world_bottom:
            # 直接杀死玩家（1 点过量伤害触发死亡流程）
            self._player.stats.take_damage(9999)
            if self._player.stats.is_dead:
                self._player.fsm.change_state("Dead")
            # 创建遗物（在地面边界附近而非实际坠落位置，避免遗物不可达）
            if self._area is not None:
                SoulFragmentSystem.create_death_relic(self._player, self._area)
                # 将遗物移到玩家最后的地面位置附近
                if self._area.death_relic:
                    self._area.death_relic.x = self._player.rect.centerx
                    self._area.death_relic.y = world_bottom - 64
            lost_souls = self._player.soul_fragments
            dx = self._player.rect.centerx
            dy = self._player.rect.centery
            self._death_screen.show(lost_souls, dx, dy)
            self._death_paused = True
            return

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

        # ---- 敌人更新 + 坠落死亡检测（第 10 阶段）----
        world_bottom = self._area.world_bounds.bottom + 128
        living = []
        for enemy in self._area.enemies:
            enemy.player = self._player
            if enemy.status._ftm is None:
                enemy.status.bind_floating_text_manager(self._floating_texts)
            enemy.attack_targets = [self._player] + getattr(self._area, "allies", [])
            enemy.update(dt, self._area.collision)
            # 坠落死亡：直接杀死，由 AI Dead 状态自动触发掉落
            if not enemy.dead and enemy.rect.top > world_bottom:
                enemy.stats.take_damage(9999)
                enemy.fsm.change_state("Dead")
            if not enemy.dead:
                living.append(enemy)
        self._area.enemies = living

        # ---- 玩家攻击框 → 敌人碰撞检测（HitResolver 接管）----
        self._hit_resolver.update(self._player, self._area.enemies)

        # ---- 抛射物更新 + 命中（玩家弓 / 敌人弓箭手 / 法师 / 毒飞镖）----
        self._update_projectiles(dt)

        # ---- 友方召唤物更新（AI + 物理 + 攻击敌人）----
        for ally in getattr(self._area, "allies", []):
            if ally.dead:
                continue
            if ally.status._ftm is None:
                ally.status.bind_floating_text_manager(self._floating_texts)
            ally.update(dt, self._area.collision)
            # 友方 AI 自动攻击敌人（由 attack_targets 驱动）
        # 清理死亡友军
        living_allies = [a for a in getattr(self._area, "allies", []) if not a.dead]
        self._area.allies = living_allies

        # ---- 地面掉落物物理 + 自动拾取（第 6 阶段）----
        ItemManager.update_drops(self._area, dt)
        ItemManager.try_pickup_all(self._player, self._area)

        self._floating_texts.update(dt)

        # ---- 第 12 阶段：通知系统更新 ----
        self._notifications.update(dt)

        # ---- 第 11 阶段：粒子特效更新 ----
        self._particle_mgr.update(dt)

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

        # 4.2 友方召唤物
        for ally in getattr(self._area, "allies", []):
            ally.render(surface, cam_offset)

        # 4.5 抛射物
        for p in getattr(self._area, "projectiles", []):
            p.render(surface, cam_offset)

        # 5. 玩家
        if self._player:
            self._player.render(surface, cam_offset)

        # 5.5. 粒子特效（第 11 阶段：世界空间粒子 + 屏幕空间粒子）
        cx, cy = cam_offset
        self._particle_mgr.render(surface, cx, cy)

        # 6. 前景遮挡层
        self._area.render_foreground(renderer, self._camera)

        # 7. HUD
        if self._player:
            self._hud.render(surface, self._player)

        # 8. 伤害飘字（覆盖在 HUD 之上）
        self._floating_texts.render(surface, cam_offset)

        # 8.5 通知系统（第 12 阶段：区域名/Boss/拾取提示）
        self._notifications.render(surface)

        # 9. 操作提示（底部）
        self._render_hints(surface)

        # 10. 背包界面（覆盖层）
        self._inv_screen.render(surface)

        # 11. 装备界面（覆盖层）
        self._equip_screen.render(surface)

        # 11.5 人物属性面板（第 12 阶段）
        if self._status_panel.is_open:
            self._status_panel.render(surface)

        # 12. 死亡界面（最高覆盖层，第 8.1 阶段）
        if self._death_screen.visible:
            self._death_screen.render(surface)

        # 13. 营地菜单（最高覆盖层，第 8.1 阶段）
        if self._campfire_menu.visible:
            self._campfire_menu.render(surface)

        # 14. 对话框（最高覆盖层，第 10 阶段）
        if self._dialogue_box.is_open():
            self._dialogue_box.render(surface)

        # 15. 商店界面（第 11 阶段扩展）
        if self._shop_screen.is_open:
            self._shop_screen.render(surface)

        pygame.display.flip()

    def _render_hints(self, surface: pygame.Surface):
        hints = [
            "A/D: 移动    Space: 跳跃    S+Space: 下穿平台",
            "Shift: 翻滚    J: 轻攻击    K: 重攻击    L: 格挡/弹反    U: 战技",
            "Q: 使用道具    F: 篝火/NPC    I: 背包    C: 装备    Tab: 属性    T: 受击    F3: 调试    ESC: 暂停",
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
    # 第 11 阶段：粒子特效事件处理
    # ----------------------------------------------------------------

    def _on_particle_hurt(self, data: dict) -> None:
        """玩家受击 → 血溅粒子。"""
        if self._player is None:
            return
        cx = self._player.rect.centerx
        cy = self._player.rect.centery
        self._particle_mgr.spawn("blood_splash", position=(cx, cy))

    def _on_particle_block(self, data: dict) -> None:
        """玩家格挡 → 盾击尘烟。"""
        if self._player is None:
            return
        cx = self._player.rect.centerx
        cy = self._player.rect.centery
        self._particle_mgr.spawn("dust", position=(cx, cy))

    def _on_particle_parry(self, data: dict) -> None:
        """弹反成功 → 金色闪光（屏幕空间） + 敌人位置血溅。"""
        if self._player is None:
            return
        # 屏幕空间金色闪光
        px = SCREEN_WIDTH // 2
        py = SCREEN_HEIGHT // 2
        self._particle_mgr.spawn("parry_flash", screen_pos=(px, py))

        # 攻击者位置的血溅
        attacker = data.get("attacker")
        if attacker is not None and hasattr(attacker, "rect") and attacker.rect is not None:
            ax = attacker.rect.centerx
            ay = attacker.rect.centery
            self._particle_mgr.spawn("blood_splash", position=(ax, ay))

    def _on_particle_dodge(self, data: dict) -> None:
        """玩家翻滚 → 灰尘粒子。"""
        if self._player is None:
            return
        cx = self._player.rect.centerx
        cy = self._player.rect.bottom
        self._particle_mgr.spawn("dust", position=(cx, cy))

    def _on_particle_status(self, data: dict) -> None:
        """状态异常 apply → 挂载对应粒子发射器到实体。"""
        entity = data.get("entity")
        status_name = data.get("status", "")
        if entity is None:
            return

        # 状态→粒子预设映射
        status_particle_map = {
            "poison": "poison",
            "burn":   "burn",
            "freeze": "freeze",
            "bleed":  "bleed",
        }
        preset = status_particle_map.get(status_name)
        if preset:
            self._particle_mgr.attach(preset, entity)

    def _on_particle_weapon_art(self, data: dict) -> None:
        """战技释放 → 魔法光效。"""
        player = data.get("player")
        if player is None:
            return
        cx = getattr(player, "rect", None)
        if cx is not None:
            self._particle_mgr.spawn("magic",
                                     position=(cx.centerx, cx.centery))

    def _on_particle_status_removed(self, data: dict) -> None:
        """状态异常移除 → 清理对应粒子发射器。"""
        entity = data.get("entity")
        status_name = data.get("status", "")
        if entity is None:
            return
        status_particle_map = {
            "poison": "poison", "burn": "burn",
            "freeze": "freeze", "bleed": "bleed",
        }
        preset = status_particle_map.get(status_name)
        if preset:
            _log.debug("_on_particle_status_removed: preset=%s entity=%s",
                       preset, type(entity).__name__)
            self._particle_mgr.remove_attached(preset, entity)

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
