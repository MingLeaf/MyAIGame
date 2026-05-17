# =============================================================
# items/item_database.py —— 物品静态注册表
#
# 第 6 阶段改造：所有 消耗品 / 护甲 / 强化材料 改为从
# data/items/*.json 加载；仅武器与默认 BossSoul 仍由代码注册
# （武器需绑定 weapon_obj，BossSoul 需要持久化 boss_id）。
#
# 使用方：
#   from items.item_database import item_db
#   item = item_db.get("estus_flask")            # 原型（共享只读）
#   item_copy = item_db.create("sword_iron")     # 创建独立副本
#
# 套装效果：item_db.set_bonuses 提供已加载的 SetBonus 列表，
# 由 SetBonusManager 注册。
# =============================================================
from __future__ import annotations

import copy
import logging
from typing import Dict, List, Optional

from items.item_base   import Item
from items.weapon      import WeaponItem
from items.armor       import ArmorItem, ArmorSlot
from items.consumable  import ConsumableItem, ConsumableEffect
from items.consumables import CONSUMABLE_FACTORIES
from items.special     import BossSoul, UpgradeMaterial
from items.equipment.set_bonus import SetBonus
from utils.json_loader import load_from_data_dir

logger = logging.getLogger(__name__)


# 字符串 → ArmorSlot 枚举
_ARMOR_SLOT_FROM_STR = {
    "head":  ArmorSlot.HEAD,
    "chest": ArmorSlot.CHEST,
    "hands": ArmorSlot.HANDS,
    "legs":  ArmorSlot.LEGS,
}


class ItemDatabase:
    """物品静态注册表，维护 id -> Item 的映射。"""

    def __init__(self):
        self._db: Dict[str, Item] = {}
        # 套装效果（list[SetBonus]）
        self.set_bonuses: List[SetBonus] = []
        self._register_all()

    # ----------------------------------------------------------------
    # 注册 & 查询接口
    # ----------------------------------------------------------------

    def register(self, item: Item, *, override: bool = False) -> None:
        """注册物品原型。"""
        if item.item_id in self._db and not override:
            raise ValueError(f"ItemDatabase: 重复注册 item_id='{item.item_id}'")
        self._db[item.item_id] = item

    def get(self, item_id: str) -> Optional[Item]:
        """返回原型（只读引用）。不存在时返回 None。"""
        return self._db.get(item_id)

    def create(self, item_id: str) -> Optional[Item]:
        """返回物品的深拷贝（背包使用，互相独立）。"""
        proto = self._db.get(item_id)
        if proto is None:
            return None
        return copy.deepcopy(proto)

    def all_items(self) -> List[Item]:
        """返回所有已注册物品原型列表。"""
        return list(self._db.values())

    def by_type(self, item_type) -> List[Item]:
        """按类型筛选物品。"""
        return [i for i in self._db.values() if i.item_type == item_type]

    # ----------------------------------------------------------------
    # 加载入口
    # ----------------------------------------------------------------

    def _register_all(self) -> None:
        # 消耗品（数据驱动）
        self._load_consumables()
        # 旧版老消耗品保留（向后兼容：estus_flask / mana_flask / herb_heal_small / antidote）
        self._register_legacy_consumables()
        # 护甲（数据驱动）
        self._load_armors()
        # 强化材料（数据驱动）
        self._load_upgrade_materials()
        # 武器（仍代码注册，需要绑定 weapon_obj）
        self._register_weapons()

    # ----------------------------------------------------------------
    # 消耗品（JSON）
    # ----------------------------------------------------------------

    def _load_consumables(self) -> None:
        try:
            cfg = load_from_data_dir("items/consumables.json")
        except FileNotFoundError:
            logger.warning("ItemDatabase: 未找到 items/consumables.json，跳过消耗品 JSON 加载")
            return
        except Exception as exc:
            logger.exception("ItemDatabase: 加载 consumables.json 失败：%s", exc)
            return

        for entry in cfg.get("consumables", []):
            kind = entry.get("type")
            cls  = CONSUMABLE_FACTORIES.get(kind)
            if cls is None:
                logger.warning("ItemDatabase: 未知消耗品类型 '%s'，跳过 %s",
                               kind, entry.get("item_id"))
                continue
            kwargs = {k: v for k, v in entry.items() if k != "type"}
            try:
                item = cls(**kwargs)
            except TypeError as exc:
                logger.exception("ItemDatabase: 构造 %s(%s) 失败：%s",
                                 kind, kwargs.get("item_id"), exc)
                continue
            self.register(item, override=True)

    def _register_legacy_consumables(self) -> None:
        """向后兼容旧 item_id（estus_flask / herb_heal_small 等）。"""
        legacy = [
            ConsumableItem(
                item_id="estus_flask",
                name="篝火烧瓶",
                description="汲取篝火之力，大量回复生命值。",
                icon_id=0,
                weight=0.3,
                effect=ConsumableEffect.HEAL,
                effect_value=60,
                max_stack=5,
            ),
            ConsumableItem(
                item_id="mana_flask",
                name="灵力瓶",
                description="蔚蓝色的液体，回复大量灵力。",
                icon_id=1,
                weight=0.3,
                effect=ConsumableEffect.RESTORE_MP,
                effect_value=30,
                max_stack=5,
            ),
            ConsumableItem(
                item_id="herb_heal_small",
                name="治愈草",
                description="林间常见的药草，小量回复生命。",
                icon_id=2,
                weight=0.1,
                effect=ConsumableEffect.HEAL,
                effect_value=20,
                max_stack=20,
            ),
        ]
        for it in legacy:
            if it.item_id in self._db:
                continue
            self.register(it)

        # 兼容旧 antidote（id=antidote）：JSON 里是 antidote_universal，
        # 旧代码可能用 "antidote" 这个 id；如果未注册则补一份占位。
        if "antidote" not in self._db:
            self.register(ConsumableItem(
                item_id="antidote",
                name="解毒药水",
                description="可消除中毒与剧毒状态。",
                icon_id=3,
                weight=0.2,
                effect=ConsumableEffect.CURE_POISON,
                effect_value=0,
                max_stack=10,
            ))

    # ----------------------------------------------------------------
    # 护甲 + 套装效果（JSON）
    # ----------------------------------------------------------------

    def _load_armors(self) -> None:
        try:
            cfg = load_from_data_dir("items/armors.json")
        except FileNotFoundError:
            logger.warning("ItemDatabase: 未找到 items/armors.json，跳过护甲 JSON 加载")
            return
        except Exception as exc:
            logger.exception("ItemDatabase: 加载 armors.json 失败：%s", exc)
            return

        for entry in cfg.get("armors", []):
            slot_str = entry.get("slot", "chest")
            slot_enum = _ARMOR_SLOT_FROM_STR.get(slot_str, ArmorSlot.CHEST)
            kwargs = {k: v for k, v in entry.items() if k != "slot"}
            try:
                item = ArmorItem(slot=slot_enum, **kwargs)
            except TypeError as exc:
                logger.exception("ItemDatabase: 构造 ArmorItem(%s) 失败：%s",
                                 entry.get("item_id"), exc)
                continue
            self.register(item, override=True)

        # 套装效果
        self.set_bonuses.clear()
        for sb_data in cfg.get("set_bonuses", []):
            try:
                sb = SetBonus(
                    set_id      = sb_data["set_id"],
                    set_name    = sb_data.get("set_name", sb_data["set_id"]),
                    threshold   = int(sb_data.get("threshold", 4)),
                    bonus       = dict(sb_data.get("bonus", {})),
                    description = sb_data.get("description", ""),
                )
                self.set_bonuses.append(sb)
            except Exception as exc:
                logger.exception("ItemDatabase: 构造 SetBonus 失败：%s", exc)

    # ----------------------------------------------------------------
    # 强化材料（JSON）
    # ----------------------------------------------------------------

    def _load_upgrade_materials(self) -> None:
        try:
            cfg = load_from_data_dir("items/upgrade_materials.json")
        except FileNotFoundError:
            logger.warning("ItemDatabase: 未找到 items/upgrade_materials.json，跳过强化材料")
            return
        except Exception as exc:
            logger.exception("ItemDatabase: 加载 upgrade_materials.json 失败：%s", exc)
            return

        for entry in cfg.get("materials", []):
            try:
                item = UpgradeMaterial(**entry)
            except TypeError as exc:
                logger.exception("ItemDatabase: 构造 UpgradeMaterial(%s) 失败：%s",
                                 entry.get("item_id"), exc)
                continue
            self.register(item, override=True)

    # ----------------------------------------------------------------
    # 武器（代码注册：需要 weapon_obj 实例）
    # ----------------------------------------------------------------

    def _register_weapons(self) -> None:
        from weapons.sword      import Sword
        from weapons.greatsword import Greatsword
        from weapons.dagger     import Dagger
        from weapons.holy_tome  import HolyTome
        from weapons.types.spear import Spear
        from weapons.types.axe   import Axe
        from weapons.types.bow   import Bow
        from weapons.types.staff import Staff

        # 武器类型 → 武器类 + 伤害标尺
        _WPN_META = {
            "sword":      (Sword,      "sword_list.json"),
            "greatsword": (Greatsword, "greatsword_list.json"),
            "dagger":     (Dagger,     "dagger_list.json"),
            "holy_tome":  (HolyTome,   "holy_tome_list.json"),
            "spear":      (Spear,      "spear_list.json"),
            "axe":        (Axe,        "axe_list.json"),
            "bow":        (Bow,        "bow_list.json"),
            "staff":      (Staff,      "staff_list.json"),
        }

        for wpn_type, (obj_cls, json_file) in _WPN_META.items():
            json_data = load_from_data_dir(f"weapons/{json_file}")
            if not json_data:
                logger.warning("ItemDatabase: 武器 JSON 不存在: weapons/%s", json_file)
                continue
            weapons = json_data.get("weapons", [])
            for w in weapons:
                item_id = w["id"]
                # 稀有度 → 伤害加成倍率
                rarity_scale = {"common": 1.0, "rare": 1.3, "legendary": 1.6}
                scale = rarity_scale.get(w.get("rarity", "common"), 1.0)
                base_atk = int((w.get("base_light_dmg", 10) + w.get("base_heavy_dmg", 20)) / 2 * scale)

                # 创建武器实例并注入 JSON 属性
                weapon_instance = obj_cls()
                sta = w.get("stamina", {})
                kb  = w.get("knockback", {})
                weapon_instance.configure(
                    display_name      = w.get("display_name", item_id),
                    color             = tuple(w.get("color", [180, 180, 180])),
                    light_dmg         = w.get("base_light_dmg"),
                    heavy_dmg         = w.get("base_heavy_dmg"),
                    element           = w.get("element", "physical"),
                    bleed_stack       = w.get("bleed_stack_light", 0.0),
                    poison_stack      = w.get("poison_stack_light", 0.0),
                    light_stamina     = sta.get("light", 12.0),
                    heavy_stamina     = sta.get("heavy", 28.0),
                    light_knockback   = kb.get("light", 160.0),
                    heavy_knockback   = kb.get("heavy", 260.0),
                )

                self.register(WeaponItem(
                    item_id     = item_id,
                    name        = w.get("display_name", item_id),
                    description = w.get("description", ""),
                    icon_id     = w.get("icon_id", 0),
                    weight      = float(sta.get("light", 12)) / 4.0,
                    base_atk    = base_atk,
                    str_scale   = 0.3 + 0.3 * scale,
                    dex_scale   = 0.3 + 0.3 * scale,
                    weapon_art  = w.get("weapon_art", ""),
                    weapon_obj  = weapon_instance,
                ))
                logger.debug("ItemDatabase: 注册武器 %s (%s) elem=%s bleed=%.0f poison=%.0f",
                             item_id, wpn_type,
                             w.get("element", "physical"),
                             w.get("bleed_stack_light", 0.0),
                             w.get("poison_stack_light", 0.0))


# 全局单例
item_db = ItemDatabase()
