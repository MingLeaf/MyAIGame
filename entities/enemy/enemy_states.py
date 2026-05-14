# =============================================================
# entities/enemy/enemy_states.py —— 兼容包装层
# =============================================================
#
# 第 7 阶段已将完整 5 态 AI 迁移到 entities/enemy/enemy_ai.py。
# 本文件保留以维持旧 import 路径的向后兼容：
#
#     from entities.enemy.enemy_states import EnemyIdleState, ATK_WINDUP_F  # 仍可用
#
# 推荐新代码直接 import enemy_ai。
# =============================================================
from entities.enemy.enemy_ai import (   # noqa: F401
    EnemyIdleState,
    EnemyAlertState,
    EnemyChaseState,
    EnemyAttackState,
    EnemyReturnState,
    EnemyHurtState,
    EnemyDeadState,
    ATK_WINDUP_F, ATK_ACTIVE_F, ATK_COOLDOWN_F,
    ATK_PHASE_WINDUP, ATK_PHASE_ACTIVE,
    ATK_PHASE_COOLDOWN, ATK_PHASE_NONE,
    HURT_DURATION, DEAD_DURATION,
    JUMP_PROBE_W, JUMP_PROBE_H, JUMP_COOLDOWN,
    register_default_states,
)
