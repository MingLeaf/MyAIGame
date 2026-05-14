# =============================================================
# systems/respawn_system.py —— 死亡复活系统
#
# 第 8 阶段：玩家死亡 → 创建遗物（灵魂碎片系统）→ 营地复活
# → 重置所有敌人 → 补满消耗品。
#
# 流程：
#   1. SoulFragmentSystem.create_death_relic(player, area)
#      → 在死亡位置放下遗物，玩家灵魂碎片归零
#   2. 查找最近激活的营地（CampfireSystem.get_last_campfire）
#   3. 将玩家传送到营地位置
#   4. 营地休息：恢复 HP/Mana/Stamina + 补满消耗品 + 重置敌人
#
# 入口：
#   RespawnSystem.handle_death(player, area)    ← 由 Player/GameScene 在死亡时调用
# =============================================================
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from core.event_manager import event_manager
from systems.soul_fragment_system import SoulFragmentSystem
from systems.campfire_system import CampfireSystem

if TYPE_CHECKING:
    from entities.player.player import Player
    from map.area import Area


class RespawnSystem:
    """
    死亡复活管理器（全静态方法）。
    """

    @staticmethod
    def handle_death(player: "Player", area: Optional["Area"] = None) -> bool:
        """
        玩家死亡时调用此方法，执行完整的复活流程。

        注意：死亡遗物由 GameScene 在显示死亡界面前创建，
        本方法仅负责传送+恢复+补消耗品+重置敌人。

        返回 True 表示复活成功。
        """
        if player is None:
            return False

        # ---- 1. 找到最近激活的营地 ----
        last_cf_id = CampfireSystem.get_last_campfire()
        spawn_pos = None
        if last_cf_id is not None:
            cf_data = CampfireSystem.get_position(last_cf_id)
            if cf_data is not None:
                spawn_pos = (cf_data.get("x", 0), cf_data.get("y", 0))

        # ---- 2. 传送玩家到营地位置 ----
        if spawn_pos is not None:
            sx, sy = spawn_pos
            player.x = sx
            player.y = sy
            player.rect.centerx = int(sx)
            player.rect.centery = int(sy)
        else:
            if area is not None:
                sx, sy = area.get_spawn_point()
                player.x = sx
                player.y = sy
                player.rect.centerx = int(sx)
                player.rect.centery = int(sy)

        # ---- 3. 重置玩家状态 ----
        player.fsm.change_state("Idle")
        player.vel_x = 0.0
        player.gravity.vel_y = 0.0
        player.gravity.set_on_ground(True)
        player.stats.hp = player.stats.max_hp
        player.stats.stamina = player.stats.max_stamina
        player.stats.mana = player.stats.max_mana
        player.invincible = False
        player.hurt_timer = 0.0

        # ---- 4. 补满消耗品 ----
        CampfireSystem._refill_consumables(player)

        # ---- 5. 重置全部敌人 ----
        if area is not None:
            try:
                area.reload()
            except Exception:
                pass

        # ---- 6. 事件广播 ----
        event_manager.emit("player_respawned", {
            "x": player.x,
            "y": player.y,
            "campfire_id": last_cf_id,
        })

        return True

    # ----------------------------------------------------------------
    # 轻量复活（仅回满血，不创建遗物）
    # ----------------------------------------------------------------

    @staticmethod
    def quick_respawn(player: "Player", area: Optional["Area"] = None) -> None:
        """
        轻量复活：不创建遗物，仅传送 + 恢复 + 重置敌人。
        用于调试或特殊场景。
        """
        last_cf_id = CampfireSystem.get_last_campfire()
        if last_cf_id is not None:
            cf_data = CampfireSystem.get_position(last_cf_id)
            if cf_data is not None:
                player.x = cf_data.get("x", player.x)
                player.y = cf_data.get("y", player.y)
                player.rect.centerx = int(player.x)
                player.rect.centery = int(player.y)

        player.fsm.change_state("Idle")
        player.vel_x = 0.0
        player.gravity.vel_y = 0.0
        player.gravity.set_on_ground(True)
        player.stats.hp = player.stats.max_hp
        player.stats.stamina = player.stats.max_stamina
        player.stats.mana = player.stats.max_mana
        player.invincible = False
        player.hurt_timer = 0.0

        CampfireSystem._refill_consumables(player)

        if area is not None:
            try:
                area.reload()
            except Exception:
                pass

        event_manager.emit("player_respawned", {
            "x": player.x,
            "y": player.y,
            "campfire_id": last_cf_id,
        })


__all__ = ["RespawnSystem"]
