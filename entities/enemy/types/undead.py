# =============================================================
# entities/enemy/types/undead.py —— 不死类
#
# 数据来源：data/entities/enemies/undead.json
# 弱点：holy / fire  抗性：poison / dark
# =============================================================
from __future__ import annotations

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for,
)


class Undead(BaseEnemy):
    """骷髅战士 / 腐骨卫兵。"""

    CATEGORY = "undead"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)
