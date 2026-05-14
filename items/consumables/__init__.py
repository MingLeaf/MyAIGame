# =============================================================
# items/consumables/__init__.py —— 消耗品分类总入口
#
# 提供消耗品类型 → 类的映射 CONSUMABLE_FACTORIES，
# 供 item_database 从 data/items/consumables.json 反射创建实例。
# =============================================================
from items.consumables.heal_potion    import HealPotion
from items.consumables.mana_potion    import ManaPotion
from items.consumables.stamina_potion import StaminaPotion
from items.consumables.antidote       import Antidote
from items.consumables.buff_items     import BuffItem
from items.consumables.special_items  import SpecialItem
from items.consumables.arrow          import ArrowItem, ARROW_ITEM_ID


# 类型字符串（出现在 JSON 的 "type" 字段） → 类
CONSUMABLE_FACTORIES = {
    "heal_potion":    HealPotion,
    "mana_potion":    ManaPotion,
    "stamina_potion": StaminaPotion,
    "antidote":       Antidote,
    "buff_item":      BuffItem,
    "special_item":   SpecialItem,
    "arrow":          ArrowItem,
}


__all__ = [
    "HealPotion", "ManaPotion", "StaminaPotion",
    "Antidote", "BuffItem", "SpecialItem", "ArrowItem",
    "ARROW_ITEM_ID",
    "CONSUMABLE_FACTORIES",
]
