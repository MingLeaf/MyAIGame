# =============================================================
# weapons/affixes/__init__.py —— 武器附魔词条系统
#
# 设计原则（来自 game_rule.md）：
#   - 词条是可装卸的修饰器，通过组合方式挂到 BaseWeapon 实例上
#   - BaseWeapon._post_process() 在每次 get_light/heavy_attack() 末尾
#     遍历 self.affixes 并依次调用 affix.modify_attack(data)
#   - 词条支持 on_attach / on_detach 钩子用于注册事件
#   - 同名词条不可重复（由 add_affix 的 not in 列表判断保证）
#
# 已实现的词条（5 类）：
#   1. ElementalEnchant —— 火/冰/雷/毒元素附魔（覆盖元素 + 状态积累 + 附加伤害）
#   2. Lifesteal       —— 吸血（5%~10% 伤害转 HP）
#   3. Swift           —— 攻速 +10%（active_frames 缩短，耐力消耗 -10%）
#   4. ArmorBreak      —— 无视 15% 防御
#   5. StatusBoost     —— 状态积累 +20%
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weapons.base_weapon import BaseWeapon, AttackData


class WeaponAffix:
    """
    词条基类。子类只需重写 modify_attack 即可。

    生命周期：
        weapon.add_affix(affix)
            → affix.on_attach(weapon)
        weapon.get_light_attack(...)
            → 内部调用 affix.modify_attack(data, is_heavy=False)
        weapon.remove_affix(affix)
            → affix.on_detach(weapon)
    """

    #: 唯一标识（如 "elemental_fire"）
    affix_id:     str = "affix"
    #: 中文显示名（用于 UI）
    display_name: str = "未命名词条"
    #: 词条品质（普通 / 稀有 / 传说），UI 着色用
    rarity:       str = "common"

    # ---- 生命周期 ----

    def on_attach(self, weapon: "BaseWeapon") -> None:
        """挂载到武器时回调（用于注册事件订阅等）。"""
        pass

    def on_detach(self, weapon: "BaseWeapon") -> None:
        """从武器卸下时回调。"""
        pass

    # ---- 主修饰器 ----

    def modify_attack(self, data: "AttackData", is_heavy: bool = False) -> "AttackData":
        """
        修改 AttackData 并返回（可原地修改）。
        默认实现：透传。
        """
        return data

    # ---- 描述 ----

    def get_description(self) -> str:
        return self.display_name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.affix_id}>"


# 子模块导入（放最后避免循环）
from weapons.affixes.elemental_enchant import (
    ElementalEnchant,
    FireEnchant, IceEnchant, LightningEnchant, PoisonEnchant,
)
from weapons.affixes.lifesteal     import LifestealAffix
from weapons.affixes.swift         import SwiftAffix
from weapons.affixes.armor_break   import ArmorBreakAffix
from weapons.affixes.status_boost  import StatusBoostAffix


__all__ = [
    "WeaponAffix",
    "ElementalEnchant",
    "FireEnchant", "IceEnchant", "LightningEnchant", "PoisonEnchant",
    "LifestealAffix",
    "SwiftAffix",
    "ArmorBreakAffix",
    "StatusBoostAffix",
]
