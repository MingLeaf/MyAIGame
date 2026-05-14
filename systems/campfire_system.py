# =============================================================
# systems/campfire_system.py —— 营地系统
#
# 第 8 阶段：管理营地激活、传送网络、休息时补充消耗品、
# 重置敌人、恢复 HP/Stamina/Mana。
#
# 游戏规则（game_rule.md §8.2）：
#   - 每个区域 1~3 个营地
#   - 营地功能：补充消耗品 / 升级 / 传送 / NPC 对话
#   - 死亡后在上一个激活的营地复活
#   - 营地休息 → 补满限定类消耗品 + 恢复 HP/Mana/Stamina
#                + 重置区域全部敌人
#
# 设计：
#   - 全局静态单例（记录已激活营地、当前复活点）
#   - 与 map/campfire.py 联动（激活时注册）
#   - 与 respawn_system.py 联动（死亡复活）
# =============================================================
from __future__ import annotations
from typing import Dict, List, Optional, Set, TYPE_CHECKING

from core.event_manager import event_manager
from systems.quest_system import QuestSystem

if TYPE_CHECKING:
    from entities.player.player import Player
    from map.area import Area


class CampfireSystem:
    """
    营地全局管理器（全静态方法）。

    核心状态：
      - _activated:     set[str]   已激活营地 ID
      - _last_campfire: str|None   最近激活的营地（复活点）
      - _positions:     dict       营地 ID → {"area_id", "x", "y"}
      - _resting:       bool       是否正在休息中
    """

    _activated: Set[str] = set()
    _last_campfire: Optional[str] = None
    _positions: Dict[str, Dict] = {}
    _resting: bool = False

    # ----------------------------------------------------------------
    # 激活营地
    # ----------------------------------------------------------------

    @classmethod
    def activate(cls, campfire_id: str, area_id: str,
                 x: float, y: float) -> bool:
        """
        激活一个营地（首次激活派发 campfire_first_activated 事件）。
        返回 True 表示首次激活。
        """
        first_time = campfire_id not in cls._activated

        cls._activated.add(campfire_id)
        cls._last_campfire = campfire_id
        cls._positions[campfire_id] = {
            "area_id": area_id,
            "x": x,
            "y": y,
        }

        # 同步到 QuestSystem
        QuestSystem.record_campfire(campfire_id)

        if first_time:
            event_manager.emit("campfire_first_activated", {
                "campfire_id": campfire_id,
                "area_id":     area_id,
                "x": x, "y": y,
            })

        event_manager.emit("campfire_activated", {
            "campfire_id": campfire_id,
            "area_id":     area_id,
            "x": x, "y": y,
            "first_time":  first_time,
        })

        return first_time

    @classmethod
    def is_activated(cls, campfire_id: str) -> bool:
        return campfire_id in cls._activated

    @classmethod
    def get_last_campfire(cls) -> Optional[str]:
        return cls._last_campfire

    @classmethod
    def get_position(cls, campfire_id: str) -> Optional[Dict]:
        return cls._positions.get(campfire_id)

    @classmethod
    def get_activated_list(cls) -> List[str]:
        return list(cls._activated)

    @classmethod
    def get_transport_targets(cls, current_id: str) -> List[Dict]:
        """
        返回可传送的营地列表（不含自身）。
        每项: {"campfire_id", "area_id", "x", "y"}
        """
        return [
            {"campfire_id": cf_id, **cls._positions[cf_id]}
            for cf_id in cls._activated
            if cf_id != current_id and cf_id in cls._positions
        ]

    # ----------------------------------------------------------------
    # 营地休息
    # ----------------------------------------------------------------

    @classmethod
    def rest(cls, player: "Player", area: Optional["Area"] = None) -> None:
        """
        营地休息：补满消耗品 + 恢复 HP/Mana/Stamina。
        注意：敌人重置由调用方（如 CampfireMenu._do_rest）显式触发。

        :param player: 玩家实例
        :param area:   已废弃（保留兼容性，不再自动重置敌人）
        """
        if cls._resting:
            return
        cls._resting = True

        try:
            # 1. 恢复 HP / Stamina / Mana
            if player is not None:
                player.stats.hp = player.stats.max_hp
                player.stats.stamina = player.stats.max_stamina
                player.stats.mana = player.stats.max_mana

                # 清除风行者状态？
                # player.clear_all_status_effects()  # TODO: 后续补

                # 2. 补满限定类消耗品（草药汤 / 高级圣水 / 灵力药剂等）
                cls._refill_consumables(player)

            # 3. 重置区域全部敌人（由调用方显式触发）
            # area.reload() 不再在此处调用

            # 事件广播
            event_manager.emit("campfire_rested", {
                "campfire_id": cls._last_campfire,
                "player_hp":   player.stats.max_hp if player else 0,
            })

        finally:
            cls._resting = False

    # ----------------------------------------------------------------
    # 消耗品补满
    # ----------------------------------------------------------------

    # 营地补满的消耗品 ID 列表（限定类）
    _REFILLABLE_IDS: Set[str] = {
        "heal_potion_small",
        "heal_potion_large",
        "mana_potion_basic",
        "stamina_potion_basic",
        "antidote_universal",
        "antidote",
        "buff_sharp_powder",
        "buff_holy_oil",
        "buff_fire_resin",
        "buff_iron_skin",
        "buff_berserker",
    }

    @classmethod
    def _refill_consumables(cls, player: "Player") -> None:
        """
        将限定类消耗品补满至上限。
        从 data/items/consumables.json 读取每个物品的 max_stack。
        """
        if player is None:
            return

        from items.item_database import item_db
        inventory = getattr(player, "inventory", None)
        if inventory is None:
            return

        refilled = []
        for item_id in cls._REFILLABLE_IDS:
            proto = item_db.get(item_id)
            if proto is None:
                continue
            max_qty = getattr(proto, "max_stack", 5)
            # 查找背包中是否有该物品（InventorySlot.item.item_id）
            found_slot = None
            for slot in inventory.slots:
                if slot is not None and getattr(slot.item, "item_id", "") == item_id:
                    found_slot = slot
                    break
            if found_slot is not None:
                qty = getattr(found_slot, "quantity", 0)
                if qty < max_qty:
                    delta = max_qty - qty
                    inventory.add(proto, delta)
                    refilled.append(item_id)
            else:
                # 物品不在背包中但属于补满范围：补至上限
                inventory.add(proto, max_qty)
                refilled.append(item_id)

        if refilled:
            event_manager.emit("consumables_refilled", {
                "count":   len(refilled),
                "item_ids": refilled,
            })


__all__ = ["CampfireSystem"]
