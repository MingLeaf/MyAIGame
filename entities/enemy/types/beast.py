# =============================================================
# entities/enemy/types/beast.py —— 野兽类
#
# 数据来源：data/entities/enemies/beast.json
# 弱点：fire  抗性：physical
# 极高移速，流血阈值低。
# =============================================================
from __future__ import annotations

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for,
)


class Beast(BaseEnemy):
    """荒原狼 / 巨型熊怪。"""

    CATEGORY = "beast"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)
