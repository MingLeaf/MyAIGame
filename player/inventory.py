# =============================================================
# player/inventory.py —— 玩家背包系统
#
# 背包最多 30 格。
# 消耗品（stackable=True）在同一格叠加，最多 max_stack 个。
# 武器/护甲各占一格（stackable=False）。
#
# 对外接口：
#   add(item, qty)      → (success: bool, leftover: int)
#   remove(slot_idx, qty) → bool
#   use_item(slot_idx, player) → bool
#   drop_item(slot_idx, qty) → bool
#   get_slot(slot_idx)  → InventorySlot | None
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from items.item_base import Item
    from entities.player.player import Player


MAX_SLOTS = 30


@dataclass
class InventorySlot:
    """背包单格：物品引用 + 数量。"""
    item:     "Item"
    quantity: int = 1

    @property
    def is_full(self) -> bool:
        return self.quantity >= self.item.max_stack

    @property
    def can_add(self) -> bool:
        return self.item.stackable and not self.is_full


class Inventory:
    """
    玩家背包，最多 MAX_SLOTS 格。

    叠加规则：
        - stackable=True 的物品在已有同 item_id 的格子上叠加，
          超出 max_stack 时溢出到下一空格。
        - stackable=False 的物品每件占一格。
    """

    def __init__(self):
        # slots[i] 为 InventorySlot 或 None（空格）
        self._slots: List[Optional[InventorySlot]] = [None] * MAX_SLOTS

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    @property
    def slots(self) -> List[Optional[InventorySlot]]:
        """返回全部格子（含空格 None）。"""
        return self._slots

    def get_slot(self, idx: int) -> Optional[InventorySlot]:
        if 0 <= idx < MAX_SLOTS:
            return self._slots[idx]
        return None

    def count(self, item_id: str) -> int:
        """统计背包内指定 item_id 的总数量。"""
        total = 0
        for s in self._slots:
            if s and s.item.item_id == item_id:
                total += s.quantity
        return total

    @property
    def free_slots(self) -> int:
        return sum(1 for s in self._slots if s is None)

    @property
    def used_slots(self) -> int:
        return MAX_SLOTS - self.free_slots

    # ----------------------------------------------------------------
    # 添加物品
    # ----------------------------------------------------------------

    def add(self, item: "Item", qty: int = 1) -> tuple[bool, int]:
        """
        向背包添加物品。
        返回 (至少加入了1个, 剩余未能加入的数量)。
        """
        if qty <= 0:
            return False, 0

        leftover = qty

        if item.stackable:
            # 先往已有同类格叠加
            for slot in self._slots:
                if slot and slot.item.item_id == item.item_id and not slot.is_full:
                    can_fit = item.max_stack - slot.quantity
                    add_now = min(can_fit, leftover)
                    slot.quantity += add_now
                    leftover -= add_now
                    if leftover == 0:
                        return True, 0

        # 开新格
        while leftover > 0:
            empty_idx = self._find_empty_slot()
            if empty_idx is None:
                break   # 背包已满
            import copy
            new_item = copy.deepcopy(item)
            take = min(item.max_stack, leftover) if item.stackable else 1
            self._slots[empty_idx] = InventorySlot(item=new_item, quantity=take)
            leftover -= take

        added = qty - leftover
        return added > 0, leftover

    # ----------------------------------------------------------------
    # 移除物品
    # ----------------------------------------------------------------

    def remove(self, slot_idx: int, qty: int = 1) -> bool:
        """从指定格子减少数量，数量归零则清空该格。"""
        slot = self.get_slot(slot_idx)
        if slot is None or qty <= 0:
            return False
        if slot.quantity < qty:
            return False
        slot.quantity -= qty
        if slot.quantity == 0:
            self._slots[slot_idx] = None
        return True

    def remove_item_id(self, item_id: str, qty: int = 1) -> bool:
        """按 item_id 从背包中减少指定数量（从最小格开始扣）。"""
        remaining = qty
        for i, slot in enumerate(self._slots):
            if slot and slot.item.item_id == item_id:
                take = min(slot.quantity, remaining)
                slot.quantity -= take
                remaining -= take
                if slot.quantity == 0:
                    self._slots[i] = None
                if remaining == 0:
                    return True
        return remaining == 0

    # ----------------------------------------------------------------
    # 使用 / 丢弃
    # ----------------------------------------------------------------

    def use_item(self, slot_idx: int, player: "Player") -> bool:
        """
        使用指定格的物品（消耗品：调用 item.use(player) 并减1）。
        武器/护甲不支持此操作（应通过 Equipment.equip 装备）。
        返回 True 表示操作成功。
        """
        slot = self.get_slot(slot_idx)
        if slot is None:
            return False
        item = slot.item
        if not item.stackable:
            return False   # 非消耗品不可"使用"

        ok = item.use(player)
        if ok:
            self.remove(slot_idx, 1)
        return ok

    def drop_item(self, slot_idx: int, qty: int = 1) -> bool:
        """
        丢弃物品（直接从背包移除，不做任何效果）。
        返回 True 表示成功移除。
        """
        return self.remove(slot_idx, qty)

    # ----------------------------------------------------------------
    # 辅助
    # ----------------------------------------------------------------

    def _find_empty_slot(self) -> Optional[int]:
        for i, s in enumerate(self._slots):
            if s is None:
                return i
        return None

    def __repr__(self) -> str:
        used = self.used_slots
        return f"<Inventory {used}/{MAX_SLOTS} slots used>"
