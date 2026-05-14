# =============================================================
# entities/enemy/types/__init__.py —— 敌人类型注册表 + 工厂
# =============================================================
#
# 第 7 阶段：所有敌人按类型放入 types/ 子目录，统一通过本注册表
# 进行查找。data_driven 工厂方法 create_enemy(category, x, y) 会
# 读取 data/entities/enemies/<category>.json 自动构造数值。
#
# 旧 import 路径（entities.enemy.infantry / undead / heavy_armor /
# beast）仍可用，由 entities/enemy/__init__.py 做兼容 re-export。
# =============================================================
from __future__ import annotations
from typing import Dict, Type

from entities.enemy.types.infantry    import Infantry
from entities.enemy.types.heavy_armor import HeavyArmor
from entities.enemy.types.undead      import Undead
from entities.enemy.types.beast       import Beast
from entities.enemy.types.archer      import Archer
from entities.enemy.types.mage        import Mage
from entities.enemy.types.elite       import Elite


# category id → 类对象
ENEMY_REGISTRY: Dict[str, Type] = {
    "infantry":    Infantry,
    "heavy_armor": HeavyArmor,
    "undead":      Undead,
    "beast":       Beast,
    "archer":      Archer,
    "mage":        Mage,
    "elite":       Elite,
}


def create_enemy(category: str, x: float, y: float):
    """
    根据类别字符串创建敌人实例。
    未知类别回退到 Infantry。
    """
    cls = ENEMY_REGISTRY.get(category, Infantry)
    return cls(float(x), float(y))


__all__ = [
    "Infantry", "HeavyArmor", "Undead", "Beast",
    "Archer", "Mage", "Elite",
    "ENEMY_REGISTRY", "create_enemy",
]
