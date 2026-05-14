# =============================================================
# entities/enemy/__init__.py —— 敌人包导出
# =============================================================
#
# 第 7 阶段重构后所有具体敌人类已迁入 entities/enemy/types/。
# 本文件 re-export 以保留旧 import 路径：
#
#     from entities.enemy import Infantry        # 仍可用
#     from entities.enemy.infantry import Infantry  # 兼容包装见下
# =============================================================
from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.types        import (
    Infantry, HeavyArmor, Undead, Beast,
    Archer, Mage, Elite,
    ENEMY_REGISTRY, create_enemy,
)

__all__ = [
    "BaseEnemy",
    "Infantry", "HeavyArmor", "Undead", "Beast",
    "Archer", "Mage", "Elite",
    "ENEMY_REGISTRY", "create_enemy",
]
