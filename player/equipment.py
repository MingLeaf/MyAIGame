# =============================================================
# player/equipment.py —— 装备栏系统
#
# 6 个槽位：weapon / shield / head / chest / hands / legs
#
# 核心逻辑：
#   equip(slot, item)   → 装备物品，更新 growth.equip_weight，
#                          并调用 stats.apply_growth() 同步数值
#   unequip(slot)       → 卸下装备，返还重量
#   get(slot)           → 获取当前槽位物品
#
# 联动：
#   装备武器后 → player.weapon = item.weapon_obj
#   装备/卸甲后 → growth.equip_weight 变化 → roll_type 自动刷新
#   → RollState.on_enter() 读取 growth.roll_params 生效
# =============================================================
from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING

from items.item_base  import Item, ItemType
from items.weapon     import WeaponItem
from items.armor      import ArmorItem, ArmorSlot

if TYPE_CHECKING:
    from entities.player.player import Player


# 槽位标识
SLOT_WEAPON = "weapon"
SLOT_SHIELD = "shield"
SLOT_HEAD   = "head"
SLOT_CHEST  = "chest"
SLOT_HANDS  = "hands"
SLOT_LEGS   = "legs"

ALL_SLOTS = [SLOT_WEAPON, SLOT_SHIELD, SLOT_HEAD, SLOT_CHEST, SLOT_HANDS, SLOT_LEGS]

# ArmorSlot 枚举值 → 装备槽位字符串
_ARMOR_SLOT_MAP = {
    ArmorSlot.HEAD:  SLOT_HEAD,
    ArmorSlot.CHEST: SLOT_CHEST,
    ArmorSlot.HANDS: SLOT_HANDS,
    ArmorSlot.LEGS:  SLOT_LEGS,
}


class Equipment:
    """
    玩家装备栏，管理 6 个槽位的装备。

    挂载方式：
        player.equipment = Equipment(player)

    每次装备/卸下后自动更新：
        - growth.equip_weight（负重率）
        - stats.atk（通过 apply_growth）
        - 翻滚参数（RollState 读取 growth.roll_params）
    """

    def __init__(self, player: "Player"):
        self._player: "Player" = player
        self._slots: Dict[str, Optional[Item]] = {s: None for s in ALL_SLOTS}

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    def get(self, slot: str) -> Optional[Item]:
        return self._slots.get(slot)

    @property
    def total_weight(self) -> float:
        """当前装备总重量（kg）。"""
        total = 0.0
        for item in self._slots.values():
            if item is not None:
                total += item.weight
        return total

    @property
    def total_defense(self) -> int:
        """四件护甲防御值之和。"""
        total = 0
        for slot in (SLOT_HEAD, SLOT_CHEST, SLOT_HANDS, SLOT_LEGS):
            item = self._slots[slot]
            if isinstance(item, ArmorItem):
                total += item.defense
        return total

    @property
    def total_poise(self) -> float:
        """四件护甲韧性之和。"""
        total = 0.0
        for slot in (SLOT_HEAD, SLOT_CHEST, SLOT_HANDS, SLOT_LEGS):
            item = self._slots[slot]
            if isinstance(item, ArmorItem):
                total += item.poise
        return total

    @property
    def total_magic_res(self) -> int:
        """四件护甲的魔法抗性之和（来自法师袍等）。"""
        total = 0
        for slot in (SLOT_HEAD, SLOT_CHEST, SLOT_HANDS, SLOT_LEGS):
            item = self._slots[slot]
            if isinstance(item, ArmorItem):
                total += getattr(item, "magic_res", 0) or 0
        return total

    # ----------------------------------------------------------------
    # 装备
    # ----------------------------------------------------------------

    def equip(self, slot: str, item: Item) -> Optional[Item]:
        """
        装备物品到指定槽位。
        返回被替换下来的旧物品（None 表示原来为空）。

        会自动校验槽位合法性：
            - weapon/shield 槽只接受 WeaponItem
            - head/chest/hands/legs 只接受对应 ArmorItem
        """
        if not self._validate_slot(slot, item):
            return None

        old_item = self._slots[slot]

        # 从负重中移除旧装备
        if old_item is not None:
            self._player.growth.equip_weight = max(
                0.0, self._player.growth.equip_weight - old_item.weight
            )
            # 若卸下武器，恢复默认武器
            if slot == SLOT_WEAPON:
                self._on_unequip_weapon()

        # 装入新装备
        self._slots[slot] = item
        self._player.growth.equip_weight += item.weight

        # 武器槽特殊处理：注入 weapon_obj 到 player.weapon
        if slot == SLOT_WEAPON and isinstance(item, WeaponItem):
            self._on_equip_weapon(item)
        elif slot == SLOT_SHIELD and isinstance(item, WeaponItem):
            pass   # 盾牌后续扩展

        # 同步数值（HP上限/耐力上限/攻击力/翻滚参数）
        self._sync_stats()

        # 发布事件
        from core.event_manager import event_manager
        event_manager.emit("equipment_changed", {
            "slot": slot,
            "item": item.item_id,
            "roll_type": self._player.growth.roll_type,
            "equip_weight": self._player.growth.equip_weight,
        })

        return old_item

    def unequip(self, slot: str) -> Optional[Item]:
        """
        卸下指定槽位的装备，归还重量。
        返回被卸下的物品（None 表示槽位为空）。
        """
        item = self._slots[slot]
        if item is None:
            return None

        self._slots[slot] = None
        self._player.growth.equip_weight = max(
            0.0, self._player.growth.equip_weight - item.weight
        )

        if slot == SLOT_WEAPON:
            self._on_unequip_weapon()

        self._sync_stats()

        from core.event_manager import event_manager
        event_manager.emit("equipment_changed", {
            "slot": slot,
            "item": None,
            "roll_type": self._player.growth.roll_type,
            "equip_weight": self._player.growth.equip_weight,
        })

        return item

    # ----------------------------------------------------------------
    # 内部
    # ----------------------------------------------------------------

    def _validate_slot(self, slot: str, item: Item) -> bool:
        """校验物品类型与槽位是否匹配。"""
        if slot not in ALL_SLOTS:
            return False
        if slot in (SLOT_WEAPON, SLOT_SHIELD):
            return isinstance(item, WeaponItem)
        # 护甲槽
        if not isinstance(item, ArmorItem):
            return False
        expected_slot = _ARMOR_SLOT_MAP.get(item.slot)
        return expected_slot == slot

    def _on_equip_weapon(self, weapon_item: WeaponItem) -> None:
        """将 weapon_obj 注入 player.weapon。"""
        if weapon_item.weapon_obj is not None:
            self._player.weapon = weapon_item.weapon_obj
        # 同步攻击力（apply_growth 内部会调用 get_atk_bonus(weapon)）

    def _on_unequip_weapon(self) -> None:
        """卸下武器后恢复裸手（使用默认 Sword 作为占位）。"""
        from weapons.sword import Sword
        self._player.weapon = Sword()

    def _sync_stats(self) -> None:
        """同步玩家数值（HP上限 / Stamina上限 / 攻击力 / 护甲防御）。"""
        p = self._player
        p.stats.apply_growth(p.growth, p.weapon)

        # ---- 第 7 阶段补丁：装备防御 + 武器物品 base_atk 注入 stats ----
        # 4 件护甲防御之和（含魔法抗性）
        p.stats.armor_defense = self.total_defense
        p.stats.magic_res_bonus = self.total_magic_res

        # 当前武器物品的 base_atk → 直接合入 player.stats.atk
        weapon_item = self._slots.get(SLOT_WEAPON)
        if weapon_item is not None and isinstance(weapon_item, WeaponItem):
            p.stats.weapon_item_atk = int(getattr(weapon_item, "base_atk", 0))
        else:
            p.stats.weapon_item_atk = 0
        # 把 weapon_item_atk 加到 stats.atk（apply_growth 已写入 growth.get_atk_bonus）
        p.stats.atk = p.stats.atk + p.stats.weapon_item_atk

    def __repr__(self) -> str:
        parts = []
        for slot in ALL_SLOTS:
            item = self._slots[slot]
            parts.append(f"{slot}={item.name if item else '空'}")
        return f"<Equipment {', '.join(parts)}>"
