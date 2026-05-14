# =============================================================
# entities/player/attack_hitbox.py —— 玩家攻击判定框（兼容层）
#
# 第 4 阶段重构：
#   实际类已迁移到 combat/hitbox.py，此处仅做向后兼容的导入别名，
#   保持旧代码 `from entities.player.attack_hitbox import AttackHitbox`
#   仍然可用。
# =============================================================
from __future__ import annotations

from combat.hitbox import (
    Hitbox as AttackHitbox,
    PHASE_WINDUP, PHASE_ACTIVE, PHASE_COOLDOWN, PHASE_NONE,
)

__all__ = [
    "AttackHitbox",
    "PHASE_WINDUP", "PHASE_ACTIVE", "PHASE_COOLDOWN", "PHASE_NONE",
]
