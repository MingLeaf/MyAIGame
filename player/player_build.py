# =============================================================
# player/player_build.py —— 玩家 Build（成长属性 + 等级）
#
# PlayerBuild 是成长属性（GrowthStats）的上层包装。
# 负责：
#   - 维护玩家等级（level）
#   - 升级时获得可分配属性点（gain_points）
#   - 分配属性点（allocate）
#   - compute_stats() 将成长属性衍生值同步到 PlayerStats
#
# 与已有系统的关系：
#   PlayerBuild.growth  ≡  player.growth  （同一 GrowthStats 对象）
#   PlayerBuild.stats   ≡  player.stats   （同一 PlayerStats 对象）
#   调用 compute_stats() 等价于 stats.apply_growth(growth, weapon)
# =============================================================
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.player.growth_stats import GrowthStats
    from entities.player.player_stats import PlayerStats
    from entities.player.player import Player
    from weapons.base_weapon import BaseWeapon


# 每个等级获得的属性点数
POINTS_PER_LEVEL = 1

# 每个等级的经验需求公式：base * level^exp_curve
EXP_BASE      = 100
EXP_CURVE     = 1.5


def exp_required(level: int) -> int:
    """计算升到 level+1 所需的经验值。"""
    return int(EXP_BASE * (level ** EXP_CURVE))


class PlayerBuild:
    """
    玩家 Build 管理器。

    用法：
        build = PlayerBuild(player)

        # 升级（通常由经验系统驱动）
        build.add_exp(500)

        # 手动分配属性点
        build.allocate("strength", 2)

        # 查询
        build.level         → 当前等级
        build.exp           → 当前经验
        build.unspent       → 待分配点数
        build.growth.vitality → 体魄点数
    """

    def __init__(self, player: "Player"):
        self._player = player
        # 直接复用 player 已有的 GrowthStats / PlayerStats
        self.growth: GrowthStats = player.growth
        self.stats:  PlayerStats = player.stats

        self.level: int = 1
        self.exp:   int = 0

    # ----------------------------------------------------------------
    # 经验 & 升级
    # ----------------------------------------------------------------

    @property
    def unspent(self) -> int:
        return self.growth.unspent_points

    @property
    def exp_to_next(self) -> int:
        return exp_required(self.level)

    def add_exp(self, amount: int) -> int:
        """
        增加经验值，自动处理连续升级。
        返回实际升了多少级。
        """
        self.exp += amount
        leveled = 0
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self._level_up()
            leveled += 1
        return leveled

    def _level_up(self) -> None:
        self.level += 1
        self.growth.gain_points(POINTS_PER_LEVEL)
        from core.event_manager import event_manager
        event_manager.emit("player_level_up", {
            "level": self.level,
            "unspent": self.growth.unspent_points,
        })

    # ----------------------------------------------------------------
    # 属性分配
    # ----------------------------------------------------------------

    def allocate(self, attr: str, points: int = 1) -> bool:
        """
        分配成长属性点并立即同步数值。
        attr: "strength" / "dexterity" / "intelligence" /
              "faith" / "vitality" / "endurance"
        """
        ok = self.growth.allocate(attr, points)
        if ok:
            self.compute_stats()
            from core.event_manager import event_manager
            event_manager.emit("player_stat_changed", {
                "attr":  attr,
                "value": getattr(self.growth, attr),
                "level": self.level,
            })
        return ok

    # ----------------------------------------------------------------
    # 数值同步
    # ----------------------------------------------------------------

    def compute_stats(self) -> None:
        """
        根据成长属性重新计算 player_stats 的衍生值：
            max_hp      = BASE_HP + vitality 加成
            max_stamina = BASE_STAMINA + endurance 加成
            atk         = GrowthStats.get_atk_bonus(current_weapon)
        由 PlayerStats.apply_growth() 实现，此方法是其对外别名。
        """
        weapon = getattr(self._player, "weapon", None)
        self.stats.apply_growth(self.growth, weapon)

    # ----------------------------------------------------------------
    # 快捷属性读取
    # ----------------------------------------------------------------

    @property
    def strength(self)     -> int: return self.growth.strength
    @property
    def dexterity(self)    -> int: return self.growth.dexterity
    @property
    def intelligence(self) -> int: return self.growth.intelligence
    @property
    def faith(self)        -> int: return self.growth.faith
    @property
    def vitality(self)     -> int: return self.growth.vitality
    @property
    def endurance(self)    -> int: return self.growth.endurance

    @property
    def max_hp(self)      -> int:   return self.stats.max_hp
    @property
    def max_stamina(self) -> float: return self.stats.max_stamina
    @property
    def atk(self)         -> int:   return self.stats.atk
    @property
    def roll_type(self)   -> str:   return self.growth.roll_type

    def __repr__(self) -> str:
        return (
            f"<PlayerBuild Lv{self.level} "
            f"STR={self.strength} DEX={self.dexterity} "
            f"INT={self.intelligence} FAITH={self.faith} "
            f"VIT={self.vitality} END={self.endurance} "
            f"unspent={self.unspent}>"
        )
