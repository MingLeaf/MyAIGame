# items/__init__.py
from items.item_base   import Item, ItemType
from items.weapon      import WeaponItem
from items.armor       import ArmorItem, ArmorSlot
from items.consumable  import ConsumableItem, ConsumableEffect
from items.item_database import item_db
from items.item_manager  import ItemManager, DroppedItem

# 子分类（消耗品/特殊/装备效果）按需导出
from items.consumables import (
    HealPotion, ManaPotion, StaminaPotion,
    Antidote, BuffItem, SpecialItem, ArrowItem, ARROW_ITEM_ID,
)
from items.special import BossSoul, UpgradeMaterial
from items.equipment import SetBonus, SetBonusManager


__all__ = [
    "Item", "ItemType",
    "WeaponItem",
    "ArmorItem", "ArmorSlot",
    "ConsumableItem", "ConsumableEffect",
    "item_db",
    "ItemManager", "DroppedItem",
    # 消耗品分类
    "HealPotion", "ManaPotion", "StaminaPotion",
    "Antidote", "BuffItem", "SpecialItem", "ArrowItem", "ARROW_ITEM_ID",
    # 特殊
    "BossSoul", "UpgradeMaterial",
    # 套装
    "SetBonus", "SetBonusManager",
]
