# =============================================================
# scenes/boss_scene.py —— Boss 战斗专用场景（独立场景版）
#
# 第 9 阶段：玩家走入雾门后 replace 当前场景为此场景。
#
# 特点：
#   - 独立场景，完全接管渲染与更新
#   - 渲染：地图 + Boss + 玩家 + HUD + Boss 血条 + 飘字
#   - 显示 Boss 专属底部血条
#   - 玩家死亡：显示死亡界面 → 营地复活 → 回到 game_scene
#   - Boss 死亡后触发清算：掉落灵核 + 解锁区域 + 回到 game_scene
# =============================================================
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

from scenes.base_scene import BaseScene
from core.camera import Camera
from core.event_manager import event_manager
from core.scene_manager import scene_manager
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from ui.hud import HUD
from combat.floating_text import FloatingTextManager
from combat.hit_resolver import HitResolver

if TYPE_CHECKING:
    from entities.enemy.bosses.base_boss import BaseBoss
    from entities.player.player import Player
    from map.area import Area


class BossScene(BaseScene):
    """
    Boss 战独立场景。全屏接管渲染和更新。

    雾门 → replace GameScene → BossScene
    Boss 死亡 → pop → GameScene
    玩家死亡 → 显示死亡界面 → 营地复活 → 回到 GameScene
    """

    def __init__(self, boss: "BaseBoss", player: "Player",
                 area: "Area", boss_room_id: str = ""):
        self._boss = boss
        self._player = player
        self._area = area
        self._room_id = boss_room_id
        self._finished = False

        # 摄像机
        self._camera = Camera()

        # HUD + 飘字
        self._hud = HUD()
        self._floating_texts = FloatingTextManager()
        self._hit_resolver = HitResolver(ftm=self._floating_texts)

        # Boss 血条
        from ui.boss_healthbar import BossHealthBar
        self._health_bar = BossHealthBar()

        # 死亡界面
        from ui.death_screen import DeathScreen
        from systems.respawn_system import RespawnSystem
        self._death_screen = DeathScreen()
        self._death_paused: bool = False

        # 状态
        self._boss_dead: bool = False
        self._finish_timer: float = 0.0

        # 将玩家传送到雾门内（Boss 房间位置）
        self._player.x = self._boss.rect.centerx - 150
        self._player.y = boss.rect.centery
        self._player.rect.centerx = int(self._player.x)
        self._player.rect.centery = int(self._player.y)

    def on_enter(self) -> None:
        self._health_bar.attach(self._boss)
        event_manager.subscribe("boss_killed", self._on_boss_killed)
        event_manager.subscribe("boss_revive_begin", self._on_revive_begin)
        event_manager.subscribe("boss_revived", self._on_revived)

    def on_exit(self) -> None:
        self._health_bar.detach()
        event_manager.unsubscribe("boss_killed", self._on_boss_killed)
        event_manager.unsubscribe("boss_revive_begin", self._on_revive_begin)
        event_manager.unsubscribe("boss_revived", self._on_revived)
        # 清理区域内的 Boss（防止回到 game_scene 后重复存在）
        if self._boss in getattr(self._area, "enemies", []):
            self._area.enemies.remove(self._boss)

    def on_pause(self) -> None:
        pass

    def on_resume(self) -> None:
        pass

    def update(self, dt: float) -> None:
        if self._finished:
            return

        # 死亡界面暂停
        if self._death_paused:
            self._death_screen.update(dt)
            return

        col = getattr(self._area, "collision", None)

        # 玩家死亡检测
        if self._player.stats.is_dead and not self._death_paused:
            if not self._player.fsm.is_in("Dead"):
                self._player.fsm.change_state("Dead")
            lost_souls = self._player.soul_fragments

            # 创建遗物
            from systems.soul_fragment_system import SoulFragmentSystem
            SoulFragmentSystem.create_death_relic(self._player, self._area)

            self._death_screen.show(lost_souls,
                                   self._player.rect.centerx,
                                   self._player.rect.centery)
            self._death_paused = True
            return

        self._health_bar.update(dt)

        # Boss 死亡清算
        if self._boss_dead:
            self._finish_timer -= dt
            if self._finish_timer <= 0.0:
                self._finish_boss()
            return

        # 更新玩家
        if col is not None:
            self._player.update(dt, col)

        # 更新 Boss
        if not self._boss.dead:
            self._boss.update(dt, col)

        # 玩家攻击 → Boss
        self._hit_resolver.update(self._player, [self._boss])

        # 飘字
        self._floating_texts.update(dt)

        # 摄像机跟随玩家
        self._camera.update(dt, self._player.rect)

        # HUD
        self._hud.update(self._player, dt)

    def handle_events(self, events: list) -> None:
        for event in events:
            # 死亡界面优先
            if self._death_screen.visible:
                action = self._death_screen.handle_event(event)
                if action == "respawn":
                    self._do_respawn()
                    return
                elif action == "quit":
                    self._do_respawn()
                    scene_manager.pop()  # 回到 game_scene 再回主菜单
                    from scenes.main_menu_scene import MainMenuScene
                    scene_manager.replace(MainMenuScene())
                    return
                if event.type == pygame.KEYDOWN:
                    continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from scenes.pause_scene import PauseScene
                    scene_manager.push(PauseScene())
                if event.key == pygame.K_F3:
                    import utils.debug as debug
                    debug.enabled = not debug.enabled

    def _do_respawn(self) -> None:
        """玩家在 Boss 战中死亡 → 营地复活 + 回到 game_scene。"""
        from systems.respawn_system import RespawnSystem
        RespawnSystem.handle_death(self._player, self._area)
        self._death_screen.hide()
        self._death_paused = False
        self._finished = True
        # 回到 game_scene
        from scenes.game_scene import GameScene
        new_game = GameScene(area_id=self._area.area_id, restart=False)
        scene_manager.clear_and_push(new_game)

    def render(self, renderer) -> None:
        surface = renderer.screen
        cam_offset = self._camera.apply_offset()

        # 背景
        surface.fill((28, 22, 35))

        # 地图 (仅背景层 + 前景遮挡，不渲染篝火等交互对象)
        self._area.render_background(renderer, self._camera)

        # Boss
        if not self._boss.dead or self._boss._revive_pending:
            self._boss.render(surface, cam_offset)

        # 玩家
        if self._player and not self._death_paused:
            self._player.render(surface, cam_offset)

        # 前景
        self._area.render_foreground(renderer, self._camera)

        # HUD
        if self._player:
            self._hud.render(surface, self._player)

        # Boss 血条
        self._health_bar.render(surface)

        # 飘字
        self._floating_texts.render(surface, cam_offset)

        # 死亡界面
        if self._death_screen.visible:
            self._death_screen.render(surface)

    # ----------------------------------------------------------------
    # 事件回调
    # ----------------------------------------------------------------

    def _on_boss_killed(self, data: dict) -> None:
        boss = data.get("boss")
        if boss is not self._boss:
            return
        self._boss_dead = True
        self._finish_timer = 2.5

    def _on_revive_begin(self, data: dict) -> None:
        pass

    def _on_revived(self, data: dict) -> None:
        self._boss_dead = False

    # ----------------------------------------------------------------
    # 清算
    # ----------------------------------------------------------------

    def _finish_boss(self) -> None:
        self._finished = True

        boss_data = getattr(self._boss, "_boss_data", {})
        boss_id = boss_data.get("id", "")
        soul_cfg = boss_data.get("boss_soul", {})
        soul_item_id = soul_cfg.get("item_id", "boss_soul_duke")
        soul_value = soul_cfg.get("soul_value", 5000)
        soul_name = soul_cfg.get("name", "Boss 之魂")

        from items.special.boss_soul import BossSoul
        soul = BossSoul(
            item_id=soul_item_id,
            name=soul_name,
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

        # 回到 game_scene（clear_and_push 替换整个栈）
        from scenes.game_scene import GameScene
        new_game = GameScene(area_id=self._area.area_id, restart=False)
        scene_manager.clear_and_push(new_game)


__all__ = ["BossScene"]
