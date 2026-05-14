# =============================================================
# weapons/affixes/elemental_enchant.py —— 元素附魔词条
#
# 功能：
#   将武器的攻击元素覆盖为指定元素（仅当原元素是 physical / none 时生效），
#   并在每次命中追加：
#     - bonus_damage : 元素附加伤害（直接加到 data.damage）
#     - X_stack      : 对应元素的状态积累（火→burn、冰→freeze、雷→shock、毒→poison）
#
# 已配置的 4 类：
#   FireEnchant       —— 火（+5 伤 / +20 burn 积累）
#   IceEnchant        —— 冰（+4 伤 / +25 freeze 积累）
#   LightningEnchant  —— 雷（+6 伤 / +15 shock 积累）
#   PoisonEnchant     —— 毒（+3 伤 / +25 poison 积累）
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from weapons.affixes import WeaponAffix

if TYPE_CHECKING:
    from weapons.base_weapon import AttackData


# ---- 元素 → (附加伤害, 状态字段名, 积累量) 的预设表 ----
_ELEMENT_PRESETS = {
    "fire":      {"bonus": 5, "status_field": "burn_stack",   "stack": 20.0,
                  "display": "炽焰附魔"},
    "ice":       {"bonus": 4, "status_field": "freeze_stack", "stack": 25.0,
                  "display": "冰封附魔"},
    "lightning": {"bonus": 6, "status_field": "shock_stack",  "stack": 15.0,
                  "display": "雷霆附魔"},
    "poison":    {"bonus": 3, "status_field": "poison_stack", "stack": 25.0,
                  "display": "剧毒附魔"},
}


class ElementalEnchant(WeaponAffix):
    """
    元素附魔基类。直接实例化即可，但更推荐使用预定义子类
    （FireEnchant / IceEnchant / LightningEnchant / PoisonEnchant）。

    构造参数：
        element   : "fire" / "ice" / "lightning" / "poison"
        bonus_dmg : 命中时附加伤害（覆盖预设）
        stack_amt : 状态积累量（覆盖预设）
    """

    affix_id     = "elemental"
    display_name = "元素附魔"
    rarity       = "rare"

    def __init__(self, element: str = "fire",
                 bonus_dmg: int = -1,
                 stack_amt: float = -1.0):
        preset = _ELEMENT_PRESETS.get(element)
        if preset is None:
            raise ValueError(f"ElementalEnchant: 未知元素 '{element}'")
        self.element:      str   = element
        self.bonus_dmg:    int   = bonus_dmg if bonus_dmg >= 0   else preset["bonus"]
        self.stack_amt:    float = stack_amt if stack_amt >= 0.0 else preset["stack"]
        self.status_field: str   = preset["status_field"]
        self.affix_id              = f"elemental_{element}"
        self.display_name          = preset["display"]

    def modify_attack(self, data: "AttackData", is_heavy: bool = False) -> "AttackData":
        # 1. 覆盖元素：仅在原元素为 physical / none 时（不破坏圣典 holy 属性）
        if data.element in ("physical", "none"):
            data.element = self.element
        # 2. 附加伤害（重攻击 ×1.5）
        bonus = self.bonus_dmg * (1.5 if is_heavy else 1.0)
        data.damage += int(bonus)
        # 3. 状态积累（重攻击 ×2）
        stack_mult = 2.0 if is_heavy else 1.0
        cur = getattr(data, self.status_field, 0.0)
        setattr(data, self.status_field, cur + self.stack_amt * stack_mult)
        return data

    def get_description(self) -> str:
        return (f"{self.display_name}：附加 +{self.bonus_dmg} {self.element} 伤害，"
                f"命中累积 {self.stack_amt:.0f} 状态值")


# ---- 预定义快捷子类 ----

class FireEnchant(ElementalEnchant):
    def __init__(self, **kw):
        super().__init__(element="fire", **kw)


class IceEnchant(ElementalEnchant):
    def __init__(self, **kw):
        super().__init__(element="ice", **kw)


class LightningEnchant(ElementalEnchant):
    def __init__(self, **kw):
        super().__init__(element="lightning", **kw)


class PoisonEnchant(ElementalEnchant):
    def __init__(self, **kw):
        super().__init__(element="poison", **kw)
