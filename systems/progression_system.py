# =============================================================
# systems/progression_system.py —— 升级成长系统
#
# 第 8 阶段：消耗灵魂碎片升级，每级获得属性点，分配到六项成长属性。
#
# 设计：
#   - 读取 data/balance/level_curve.json 获取每级成本
#   - 玩家在营地消耗灵魂碎片升级（可连续升级）
#   - 升级获得属性点（POINTS_PER_LEVEL = 1），由玩家分配
#   - 分配后立即同步 PlayerStats 衍生值
#
# 与 PlayerBuild 的关系：
#   - ProgressionSystem 是上层升级逻辑
#   - PlayerBuild 是等级/经验的容器（薄包装/兼容旧接口）
#   - ProgressionSystem.spend_souls_to_level_up(player, levels)
#      → 消耗 player.soul_fragments，逐级调用 build._level_up()
#
# 使用：
#   from systems.progression_system import ProgressionSystem
#   ProgressionSystem.spend_souls_to_level_up(player, 5)  # 尝试升 5 级
#   ProgressionSystem.get_level_cost(5)                   # 查询升到 Lv5 的成本
# =============================================================
from __future__ import annotations
from typing import Optional, TYPE_CHECKING, List
import logging

from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player

logger = logging.getLogger(__name__)


class ProgressionSystem:
    """
    升级管理器（全静态方法）。
    """

    _level_data: Optional[List[dict]] = None
    _points_per_level: int = 1
    _max_level: int = 50
    _loaded: bool = False

    # ----------------------------------------------------------------
    # 数据加载
    # ----------------------------------------------------------------

    @classmethod
    def load_data(cls) -> None:
        """从 data/balance/level_curve.json 加载等级数据。"""
        if cls._loaded:
            return
        cls._loaded = True

        try:
            from utils.json_loader import load_from_data_dir
            cfg = load_from_data_dir("balance/level_curve.json")
            cls._max_level = cfg.get("max_level", 50)
            cls._points_per_level = cfg.get("points_per_level", 1)
            cls._level_data = cfg.get("levels", [])
            if not cls._level_data:
                cls._build_fallback_curve()
        except Exception:
            logger.warning("ProgressionSystem: 无法加载 level_curve.json，使用内置曲线")
            cls._build_fallback_curve()

    @classmethod
    def _build_fallback_curve(cls) -> None:
        """内置回退曲线（JSON 缺失时使用）。"""
        cls._level_data = []
        base, exp = 120, 1.38
        for lv in range(1, cls._max_level + 1):
            cost = int(base * (lv ** exp))
            cost = (cost // 10) * 10  # 取整到 10
            cls._level_data.append({"level": lv, "cost": cost})

    # ----------------------------------------------------------------
    # 成本查询
    # ----------------------------------------------------------------

    @classmethod
    def get_level_cost(cls, level: int) -> int:
        """
        查询升到指定等级（从上一级升到该级）所需的灵魂碎片数。
        level=1 是初始等级，无需成本。
        """
        cls.load_data()
        if level <= 1:
            return 0
        idx = level - 1
        if cls._level_data and 0 <= idx < len(cls._level_data):
            return cls._level_data[idx].get("cost", 0)
        # 回退公式
        return int(120 * (level ** 1.38))

    @classmethod
    def get_total_cost_to_level(cls, target_level: int) -> int:
        """计算从 Lv1 升到 target_level 的总成本。"""
        total = 0
        for lv in range(2, target_level + 1):
            total += cls.get_level_cost(lv)
        return total

    @classmethod
    def get_max_level(cls) -> int:
        cls.load_data()
        return cls._max_level

    @classmethod
    def get_points_per_level(cls) -> int:
        cls.load_data()
        return cls._points_per_level

    # ----------------------------------------------------------------
    # 升级逻辑
    # ----------------------------------------------------------------

    @classmethod
    def spend_souls_to_level_up(cls, player: "Player", levels: int = 1) -> int:
        """
        消耗灵魂碎片，尝试升级指定次数。
        返回实际升级的级数（0 表示灵魂不足或已满级）。

        :param player: 玩家实例
        :param levels: 期望升级级数
        """
        cls.load_data()
        if player is None or levels <= 0:
            return 0

        build = getattr(player, "build", None)
        if build is None:
            return 0

        soul_fragments = getattr(player, "soul_fragments", 0)
        current_level = build.level
        max_lv = cls._max_level

        leveled = 0
        spent_total = 0

        for _ in range(levels):
            next_level = current_level + 1
            if next_level > max_lv:
                break
            cost = cls.get_level_cost(next_level)
            if soul_fragments < cost:
                break

            # 扣灵魂碎片
            soul_fragments -= cost
            spent_total += cost

            # 升级（使用 PlayerBuild 的内部方法）
            build.exp += cost  # 将灵魂碎片量视为经验
            # 直接调用底层升级
            old_level = build.level
            build._level_up()
            current_level = build.level
            leveled += 1

        # 写回灵魂碎片
        player.soul_fragments = soul_fragments

        if leveled > 0:
            event_manager.emit("player_leveled_up", {
                "levels":      leveled,
                "new_level":   current_level,
                "spent_souls": spent_total,
                "unspent":     build.unspent,
            })

        return leveled

    # ----------------------------------------------------------------
    # 属性点分配（委托给 Player.allocate_stat）
    # ----------------------------------------------------------------

    @classmethod
    def allocate_attribute(cls, player: "Player", attr: str, points: int = 1) -> bool:
        """
        分配成长属性点。
        委托给 player.allocate_stat(attr, points)。
        """
        if player is None:
            return False
        return player.allocate_stat(attr, points)


__all__ = ["ProgressionSystem"]
