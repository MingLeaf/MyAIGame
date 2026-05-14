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

        sword_obj = Sword()
        self.register(WeaponItem(
            item_id     = "sword_iron",
            name        = "铁制骑士剑",
            description = "标准骑士剑，攻守均衡。战技：旋风斩 — 360度旋转斩击，打飞周围敌人。",
            icon_id     = 10,
            weight      = 3.0,
            base_atk    = 22,
            str_scale   = 0.5,
            dex_scale   = 0.5,
            weapon_art  = "旋风斩",
            weapon_obj  = sword_obj,
        ))

        from weapons.greatsword import Greatsword
        gs_obj = Greatsword()
        self.register(WeaponItem(
            item_id     = "greatsword_iron",
            name        = "铁制大剑",
            description = "沉重的大剑，一击可撼动盾牌。战技：天崩地裂 — 跳起重劈，震地击晕。",
            icon_id     = 11,
            weight      = 6.0,
            base_atk    = 45,
            str_scale   = 0.8,
            dex_scale   = 0.0,
            weapon_art  = "天崩地裂",
            weapon_obj  = gs_obj,
        ))

        from weapons.dagger import Dagger
        dagger_obj = Dagger()
        self.register(WeaponItem(
            item_id     = "dagger_bone",
            name        = "骨刃匕首",
            description = "轻巧短刃，连击速度极快，易造成流血。战技：幻影步 — 瞬移至敌人身后背刺。",
            icon_id     = 12,
            weight      = 1.0,
            base_atk    = 15,
            str_scale   = 0.0,
            dex_scale   = 0.8,
            weapon_art  = "幻影步",
            weapon_obj  = dagger_obj,
        ))

        from weapons.holy_tome import HolyTome
        holy_obj = HolyTome()
        self.register(WeaponItem(
            item_id     = "holy_tome_basic",
            name        = "信徒圣典",
            description = "信仰者的圣经，可施展神圣奇迹。战技：神圣之光 — 释放冲击波+自我治疗。",
            icon_id     = 13,
            weight      = 1.5,
            base_atk    = 5,
            str_scale   = 0.0,
            dex_scale   = 0.0,
            weapon_art  = "神圣之光",
            weapon_obj  = holy_obj,
        ))


# 全局单例
item_db = ItemDatabase()
