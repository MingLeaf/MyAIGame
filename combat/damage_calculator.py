# =============================================================
# combat/damage_calculator.py —— 伤害计算器
#
# 公式（来自 game_rule.md）：
#   最终伤害 = max(1, 攻击力 × 技能倍率 - 防御值 × 防御系数)
#   弱点/克制 → 查 EnemyStats.get_damage_multiplier(element)
#   背刺      × 1.5
#   格挡减伤  30%~80%（默认 50%）
#
# 元素克制优先级（高→低）：
#   EnemyStats.immunities  → ×0  （完全免疫）
#   EnemyStats.weaknesses  → ×1.5（弱点）
#   EnemyStats.resistances → ×0.5（抗性）
#   全局 _ELEMENT_BONUS 表 → 兜底克制（如神圣克不死 ×1.5）
# =============================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.enemy.enemy_stats import EnemyStats


# ---------- 元素常量 ----------
class Element:
    NONE   = "none"
    FIRE   = "fire"
    ICE    = "ice"
    HOLY   = "holy"
    POISON = "poison"
    DARK   = "dark"
    LIGHTNING = "lightning"
    PHYSICAL  = "physical"


# ----------------------------------------------------------------
# 数值配置：从 data/balance/damage_formula.json 加载（带兜底）
# 第 4 阶段·数据驱动重构
# ----------------------------------------------------------------

# 全局兜底克制表（当 EnemyStats 没有显式配置 weaknesses/resistances 时生效）
# key: (攻击元素, 防御者种族标签)  value: 倍率
_GLOBAL_ELEMENT_BONUS: dict[tuple[str, str], float] = {
    (Element.HOLY,      "undead"):    1.5,
    (Element.FIRE,      "beast"):     1.3,
    (Element.HOLY,      "construct"): 1.3,
    (Element.LIGHTNING, "construct"): 1.5,
    (Element.POISON,    "human"):     1.3,
}

# 格挡减伤系数范围（默认值，可被 JSON 覆盖）
_BLOCK_REDUCE_MIN = 0.30
_BLOCK_REDUCE_MAX = 0.80
_BLOCK_REDUCE_DEF = 0.50

# 防御系数（默认值，可被 JSON 覆盖）
_DEFENSE_COEFF = 0.50

# 弱点 / 背刺倍率（默认值，可被 JSON 覆盖）
_BACKSTAB_MULT   = 1.5
_WEAK_POINT_MULT = 1.5

# 最低伤害下限
_MIN_DAMAGE = 1


def _load_balance_config() -> None:
    """从 data/balance/damage_formula.json 覆盖默认数值。失败则保持兜底常量。"""
    global _DEFENSE_COEFF, _BLOCK_REDUCE_MIN, _BLOCK_REDUCE_MAX, _BLOCK_REDUCE_DEF
    global _BACKSTAB_MULT, _WEAK_POINT_MULT, _MIN_DAMAGE
    try:
        from utils.json_loader import load_from_data_dir
        cfg = load_from_data_dir("balance/damage_formula.json")
    except Exception:
        return

    _DEFENSE_COEFF     = float(cfg.get("defense_coeff",        _DEFENSE_COEFF))
    _BLOCK_REDUCE_MIN  = float(cfg.get("block_reduce_min",     _BLOCK_REDUCE_MIN))
    _BLOCK_REDUCE_MAX  = float(cfg.get("block_reduce_max",     _BLOCK_REDUCE_MAX))
    _BLOCK_REDUCE_DEF  = float(cfg.get("block_reduce_default", _BLOCK_REDUCE_DEF))
    _BACKSTAB_MULT     = float(cfg.get("backstab_multiplier",  _BACKSTAB_MULT))
    _WEAK_POINT_MULT   = float(cfg.get("weak_point_multiplier",_WEAK_POINT_MULT))
    _MIN_DAMAGE        = int(cfg.get("min_damage",             _MIN_DAMAGE))

    # 元素克制表覆盖
    bonus_list = cfg.get("global_element_bonus", [])
    if bonus_list:
        _GLOBAL_ELEMENT_BONUS.clear()
        for entry in bonus_list:
            elem = entry.get("element")
            tag  = entry.get("tag")
            mult = float(entry.get("multiplier", 1.0))
            if elem and tag:
                _GLOBAL_ELEMENT_BONUS[(elem, tag)] = mult


# 模块导入时尝试加载一次
_load_balance_config()


@dataclass
class HitInfo:
    """单次命中的附加信息，传给 DamageCalculator.calculate()"""
    base_damage:      int       = 10           # 攻击框原始伤害值
    skill_multiplier: float     = 1.0          # 技能倍率（普通攻击=1.0）
    element:          str       = Element.NONE  # 攻击元素
    is_backstab:      bool      = False         # 背刺（×1.5）
    is_weak_point:    bool      = False         # 命中弱点（×1.5，已包含在 element 克制中可选叠加）
    is_blocked:       bool      = False         # 被格挡
    block_reduce:     float     = _BLOCK_REDUCE_DEF  # 格挡减伤比例
    poise_damage:     float     = 10.0          # 对韧性的伤害量


@dataclass
class AttackerStats:
    """攻击方需要的数值切片"""
    atk: int = 10


@dataclass
class DefenderStats:
    """防御方需要的数值切片（兼容 EnemyStats 和 PlayerStats）"""
    defense: int = 0
    # 可选：直接传入 EnemyStats 对象以获取克制信息
    enemy_stats: Optional["EnemyStats"] = field(default=None, repr=False)


class DamageCalculator:
    """
    无状态伤害计算器。

    用法：
        calc = DamageCalculator()
        dmg  = calc.calculate(attacker_stats, defender_stats, hit_info)

    若 defender_stats.enemy_stats 不为 None，则优先使用其
    weaknesses/resistances/immunities 查克制关系。
    """

    @staticmethod
    def calculate(
        attacker_stats: AttackerStats,
        defender_stats: DefenderStats,
        hit_info:       HitInfo,
    ) -> int:
        """
        计算最终伤害，返回 int（≥ 1）。

        步骤：
          1. base = (attacker_stats.atk + hit_info.base_damage) × skill_multiplier
             ※ attacker_stats.atk 为角色攻击力加成，base_damage 为武器/技能固定值
          2. 减防御：net = base - defense × DEFENSE_COEFF
          3. 元素克制倍率（优先 EnemyStats 配置，兜底全局表）
          4. 背刺/弱点
          5. 格挡减伤
          6. clamp(1, ∞)
        """
        # 1. 基础伤害 = 攻击力加成 + 武器固定值，再乘技能倍率
        raw: float = (attacker_stats.atk + hit_info.base_damage) * hit_info.skill_multiplier

        # 2. 防御减免
        raw -= defender_stats.defense * _DEFENSE_COEFF

        # 3. 元素克制
        elem = hit_info.element
        if elem and elem != Element.NONE:
            estats = defender_stats.enemy_stats
            if estats is not None and hasattr(estats, "get_damage_multiplier"):
                # 优先使用 EnemyStats 上的克制配置
                mult = estats.get_damage_multiplier(elem)
                raw *= mult
            else:
                # 兜底：查全局克制表（需要 defender_tags 字段，但此版本已移除）
                # 这里走全局表时需要 element_tags，通过 enemy_stats 获取
                if estats is not None:
                    for tag in getattr(estats, "element_tags", []):
                        key = (elem, tag)
                        if key in _GLOBAL_ELEMENT_BONUS:
                            raw *= _GLOBAL_ELEMENT_BONUS[key]
                            break

        # 4. 弱点（背刺 or 显式弱点命中）
        if hit_info.is_weak_point:
            raw *= _WEAK_POINT_MULT
        if hit_info.is_backstab:
            raw *= _BACKSTAB_MULT

        # 5. 格挡减伤
        if hit_info.is_blocked:
            reduce = max(_BLOCK_REDUCE_MIN,
                         min(_BLOCK_REDUCE_MAX, hit_info.block_reduce))
            raw *= (1.0 - reduce)

        # 6. 最低伤害下限
        return max(_MIN_DAMAGE, int(raw))
