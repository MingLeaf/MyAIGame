# =============================================================
# weapons/types/__init__.py —— 武器子类型聚合导出
#
# 把 weapons 包按"基础四件"+"types/ 扩展四件"组织：
#   - 基础四件：Sword / Greatsword / Dagger / HolyTome
#     位于 weapons/{sword,greatsword,dagger,holy_tome}.py
#   - 扩展四件：Spear / Axe / Bow / Staff
#     位于 weapons/types/{spear,axe,bow,staff}.py
#
# 同时提供 WEAPON_REGISTRY，用于按 weapon_type 字符串查类。
# =============================================================
from __future__ import annotations

from weapons.base_weapon import WeaponType
from weapons.sword       import Sword
from weapons.dagger      import Dagger
from weapons.greatsword  import Greatsword
from weapons.holy_tome   import HolyTome

from weapons.types.spear import Spear
from weapons.types.axe   import Axe
from weapons.types.bow   import Bow
from weapons.types.staff import Staff


WEAPON_REGISTRY = {
    WeaponType.SWORD:      Sword,
    WeaponType.DAGGER:     Dagger,
    WeaponType.GREATSWORD: Greatsword,
    WeaponType.HOLY_TOME:  HolyTome,
    WeaponType.SPEAR:      Spear,
    WeaponType.AXE:        Axe,
    WeaponType.BOW:        Bow,
    WeaponType.STAFF:      Staff,
}


def create_weapon(weapon_type: str):
    """按字符串类型快速创建武器实例。"""
    cls = WEAPON_REGISTRY.get(weapon_type)
    if cls is None:
        raise ValueError(f"create_weapon: 未知武器类型 '{weapon_type}'")
    return cls()


__all__ = [
    "Sword", "Dagger", "Greatsword", "HolyTome",
    "Spear", "Axe", "Bow", "Staff",
    "WEAPON_REGISTRY", "create_weapon",
]
