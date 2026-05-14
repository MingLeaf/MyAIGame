# =============================================================
# entities/enemy/types/heavy_armor.py —— 重甲兵
#
# 数据来源：data/entities/enemies/heavy_armor.json
# 弱点：lightning  抗性：physical/fire  免疫：poison
# 高韧性，重击才能打断；强力击退。
# =============================================================
from __future__ import annotations

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for,
)


class HeavyArmor(BaseEnemy):
    """石像骑士 / 铁甲卫兵。"""

    CATEGORY = "heavy_armor"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)
