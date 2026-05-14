# =============================================================
# weapons/__init__.py —— 武器系统统一导出（第 5 阶段补完）
# =============================================================
from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.sword       import Sword
from weapons.dagger      import Dagger
from weapons.greatsword  import Greatsword
from weapons.holy_tome   import HolyTome

# 第 5 阶段新增 4 类（位于 weapons/types/）
from weapons.types.spear import Spear
from weapons.types.axe   import Axe
from weapons.types.bow   import Bow
from weapons.types.staff import Staff

# 战技 + 强化 + 词条
from weapons.weapon_art     import WeaponArt
from weapons.weapon_upgrade import WeaponUpgrade, UpgradeRoute, get_default_upgrader
from weapons.affixes        import (
    WeaponAffix,
    ElementalEnchant,
    FireEnchant, IceEnchant, LightningEnchant, PoisonEnchant,
    LifestealAffix, SwiftAffix, ArmorBreakAffix, StatusBoostAffix,
)

# 类型注册表 + 工厂
from weapons.types import WEAPON_REGISTRY, create_weapon


__all__ = [
    # 基础
    "BaseWeapon", "WeaponType", "AttackData",
    # 8 类武器
    "Sword", "Dagger", "Greatsword", "HolyTome",
    "Spear", "Axe", "Bow", "Staff",
    # 战技 + 强化
    "WeaponArt",
    "WeaponUpgrade", "UpgradeRoute", "get_default_upgrader",
    # 词条
    "WeaponAffix",
    "ElementalEnchant",
    "FireEnchant", "IceEnchant", "LightningEnchant", "PoisonEnchant",
    "LifestealAffix", "SwiftAffix", "ArmorBreakAffix", "StatusBoostAffix",
    # 工厂
    "WEAPON_REGISTRY", "create_weapon",
]
