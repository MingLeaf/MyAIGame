# =============================================================
# entities/player/growth_stats.py —— 玩家成长属性系统
#
# 对应 game_rule.md §2.2 成长属性（可通过升级分配点数）
#
# 六项成长属性：
#   力量(STR)  : 提升重型武器伤害 + 满足装备要求
#   敏捷(DEX)  : 提升轻型/速度型武器伤害 + 翻滚距离
#   智慧(INT)  : 提升魔法伤害
#   信仰(FAITH): 提升神圣类技能 + 治疗效果
#   体魄(VIT)  : 提升最大HP + 耐力恢复速度
#   耐性(END)  : 提升最大Stamina + 最大负重
#
# 衍生属性（§2.3）：
#   物理攻击力 = 武器基础攻击 + STR加成(重武器) or DEX加成(轻武器)
#   最大HP     = BASE_HP  + VIT × HP_PER_VIT
#   最大Stamina= BASE_STA + END × STA_PER_END
#   最大负重   = BASE_LOAD + END × LOAD_PER_END
#   翻滚类型   = 当前负重率(<30%快/30~70%中/>70%慢/>100%无法)
# =============================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weapons.base_weapon import BaseWeapon


# ---- 成长系数常量 ----
HP_PER_VIT      = 15       # 每点体魄提升最大HP
STA_PER_END     = 10       # 每点耐性提升最大Stamina
LOAD_PER_END    = 5.0      # 每点耐性提升最大负重(kg)
BASE_LOAD       = 30.0     # 初始最大负重(kg)
ATK_PER_STR     = 0.5      # 每点力量提升物理攻击力（重武器系数）
ATK_PER_DEX     = 0.5      # 每点敏捷提升物理攻击力（轻武器系数）
MAGIC_PER_INT   = 0.8      # 每点智慧提升魔法攻击力
HOLY_PER_FAITH  = 0.8      # 每点信仰提升神圣攻击力


# ---- 翻滚类型 ----
class RollType:
    FAST     = "fast"      # 负重率 < 30%：快滚（距离最远，无敌帧最多）
    NORMAL   = "normal"    # 负重率 30~70%：中滚
    SLOW     = "slow"      # 负重率 70~100%：慢滚（距离短，无敌帧少）
    UNABLE   = "unable"    # 负重率 > 100%：无法翻滚

# 各翻滚类型的速度、持续时间、无敌帧区间
ROLL_PARAMS: dict[str, dict] = {
    RollType.FAST:   {"speed": 480.0, "duration": 0.30, "inv_start": 0.04, "inv_end": 0.22},
    RollType.NORMAL: {"speed": 400.0, "duration": 0.35, "inv_start": 0.05, "inv_end": 0.26},
    RollType.SLOW:   {"speed": 300.0, "duration": 0.42, "inv_start": 0.06, "inv_end": 0.22},
    RollType.UNABLE: {"speed": 0.0,   "duration": 0.0,  "inv_start": 0.0,  "inv_end": 0.0},
}


@dataclass
class GrowthStats:
    """
    玩家六项成长属性容器。

    挂载方式：
        player.growth = GrowthStats()

    升级分配：
        player.growth.allocate("strength", 1)

    读取衍生值：
        player.growth.get_atk_bonus(weapon)   → 物理攻击加成
        player.growth.max_hp_bonus            → HP上限加成
        player.growth.roll_type               → 翻滚类型
    """

    # ---- 六项成长属性（初始均为 10）----
    strength:     int = 10    # 力量 STR
    dexterity:    int = 10    # 敏捷 DEX
    intelligence: int = 5     # 智慧 INT
    faith:        int = 5     # 信仰 FAITH
    vitality:     int = 10    # 体魄 VIT
    endurance:    int = 10    # 耐性 END

    # ---- 装备负重（由装备系统写入）----
    equip_weight: float = field(default=0.0, repr=False)  # 当前装备总重量(kg)

    # ---- 可分配点数（每次升级+1）----
    unspent_points: int = 0

    # ----------------------------------------------------------------
    # 升级接口
    # ----------------------------------------------------------------

    def allocate(self, attr: str, points: int = 1) -> bool:
        """
        分配属性点。
        attr 支持: "strength","dexterity","intelligence","faith","vitality","endurance"
        返回 True 表示分配成功。
        """
        _valid = {"strength", "dexterity", "intelligence",
                  "faith", "vitality", "endurance"}
        if attr not in _valid:
            raise ValueError(f"无效属性名: {attr}")
        if self.unspent_points < points:
            return False
        setattr(self, attr, getattr(self, attr) + points)
        self.unspent_points -= points
        return True

    def gain_points(self, n: int = 1) -> None:
        """升级时获得可分配点数。"""
        self.unspent_points += n

    # ----------------------------------------------------------------
    # 衍生：物理攻击加成
    # ----------------------------------------------------------------

    def get_atk_bonus(self, weapon: "BaseWeapon | None" = None) -> int:
        """
        计算角色物理攻击加成（叠加到武器 base_damage）。

        规则：
          - 大剑/战斧(GREATSWORD/AXE)：使用力量加成
          - 匕首/弓(DAGGER/BOW)：使用敏捷加成
          - 单手剑/长矛(SWORD/SPEAR)：取 STR 和 DEX 中较高者
          - 法杖/圣典：使用 INT/FAITH 加成，物理加成为 0
        """
        from weapons.base_weapon import WeaponType

        if weapon is None:
            return int((self.strength + self.dexterity) * ATK_PER_STR / 2)

        wt = weapon.weapon_type
        if wt in (WeaponType.GREATSWORD, WeaponType.AXE):
            return int(self.strength * ATK_PER_STR)
        elif wt in (WeaponType.DAGGER, WeaponType.BOW):
            return int(self.dexterity * ATK_PER_DEX)
        elif wt in (WeaponType.STAFF, WeaponType.HOLY_TOME):
            return 0   # 法术类武器不计物理加成
        else:
            # 单手剑/长矛等均衡型：取 STR、DEX 中较高者
            return int(max(self.strength * ATK_PER_STR,
                           self.dexterity * ATK_PER_DEX))

    def get_magic_atk_bonus(self) -> int:
        """魔法攻击加成（智慧）。"""
        return int(self.intelligence * MAGIC_PER_INT)

    def get_holy_atk_bonus(self) -> int:
        """神圣攻击加成（信仰）。"""
        return int(self.faith * HOLY_PER_FAITH)

    # ----------------------------------------------------------------
    # 衍生：HP / Stamina 上限加成
    # ----------------------------------------------------------------

    @property
    def max_hp_bonus(self) -> int:
        """体魄对最大HP的加成值。"""
        return (self.vitality - 10) * HP_PER_VIT   # 基准10点，超出才加成

    @property
    def max_stamina_bonus(self) -> float:
        """耐性对最大耐力的加成值。"""
        return float((self.endurance - 10) * STA_PER_END)

    # ----------------------------------------------------------------
    # 衍生：负重与翻滚类型
    # ----------------------------------------------------------------

    @property
    def max_equip_load(self) -> float:
        """最大负重量（kg）。"""
        return BASE_LOAD + (self.endurance - 10) * LOAD_PER_END

    @property
    def equip_load_ratio(self) -> float:
        """当前负重率 [0.0, ∞)，1.0 = 满载。"""
        max_load = self.max_equip_load
        return self.equip_weight / max_load if max_load > 0 else float("inf")

    @property
    def roll_type(self) -> str:
        """
        根据负重率返回翻滚类型（game_rule.md §2.3）。
          < 30%  → FAST
          30~70% → NORMAL
          70~100%→ SLOW
          > 100% → UNABLE
        """
        ratio = self.equip_load_ratio
        if ratio > 1.0:
            return RollType.UNABLE
        elif ratio > 0.70:
            return RollType.SLOW
        elif ratio >= 0.30:
            return RollType.NORMAL
        else:
            return RollType.FAST

    @property
    def roll_params(self) -> dict:
        """返回当前翻滚类型对应的速度/持续时间/无敌帧参数。"""
        return ROLL_PARAMS[self.roll_type]

    # ----------------------------------------------------------------
    # 调试展示
    # ----------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<GrowthStats STR={self.strength} DEX={self.dexterity} "
            f"INT={self.intelligence} FAITH={self.faith} "
            f"VIT={self.vitality} END={self.endurance} "
            f"load={self.equip_weight:.1f}/{self.max_equip_load:.1f}kg "
            f"roll={self.roll_type}>"
        )
