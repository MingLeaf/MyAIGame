# =============================================================
# combat/status_effects.py —— 状态异常（兼容别名）
#
# 第 4 阶段重构：实际实现位于 combat/status_effect.py
# 此处仅做导入聚合，对应开发文档中的命名 status_effects.py
# =============================================================
from __future__ import annotations

from combat.status_effect import (
    StatusEffect,
    BleedEffect,
    PoisonEffect,
    BurnEffect,
    FreezeEffect,
    CurseEffect,
    StunEffect,
)

__all__ = [
    "StatusEffect",
    "BleedEffect",
    "PoisonEffect",
    "BurnEffect",
    "FreezeEffect",
    "CurseEffect",
    "StunEffect",
]
