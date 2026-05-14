# =============================================================
# combat/__init__.py —— 战斗系统包
# =============================================================
from combat.damage_calculator import DamageCalculator, HitInfo
from combat.hit_resolver      import HitResolver
from combat.status_effect     import (
    StatusEffect,
    BleedEffect,
    PoisonEffect,
    BurnEffect,
    FreezeEffect,
)
from combat.status_manager    import StatusManager
from combat.floating_text     import FloatingText, FloatingTextManager

__all__ = [
    "DamageCalculator", "HitInfo",
    "HitResolver",
    "StatusEffect", "BleedEffect", "PoisonEffect", "BurnEffect", "FreezeEffect",
    "StatusManager",
    "FloatingText", "FloatingTextManager",
]
