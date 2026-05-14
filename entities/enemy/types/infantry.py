# =============================================================
# entities/enemy/types/infantry.py —— 普通步兵
#
# 数据来源：data/entities/enemies/infantry.json
# 弱点：holy（神圣 ×1.5）
# =============================================================
from __future__ import annotations

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for,
)


class Infantry(BaseEnemy):
    """腐化步兵 / 亡灵剑士。完整数值见 data/entities/enemies/infantry.json"""

    CATEGORY = "infantry"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        # drop_table 基于实例创建，避免污染类属性
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)
