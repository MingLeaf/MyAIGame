# =============================================================
# entities/enemy/enemy_stats.py —— 敌人数值系统
# =============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from combat.poise_system import PoiseComponent


@dataclass
class EnemyStats:
    """
    敌人基础数值容器。
    每种敌人通过传入不同的初始值来区分强度。

    克制与抗性：
      element_tags    : 该敌人所属的元素/种族标签（供 DamageCalculator 查克制关系）
                        e.g. ["undead"], ["beast"], ["fire_immune"]
      weaknesses      : 弱点元素列表，受到该元素伤害时额外 ×1.5
      resistances     : 抗性元素列表，受到该元素伤害时减伤 ×0.5
      immunities      : 免疫元素列表，受到该元素伤害时归零
      bleed_threshold : 触发流血爆发所需的积累值（数值越高越难触发）
      poise:          : 韧性值，归零后触发眩晕
    """

    # ---- 基础属性 ----
    max_hp:   int   = 60          # 最大生命值
    hp:       int   = field(init=False)   # 当前生命值（等于 max_hp）
    atk:      int   = 12          # 攻击力（普通攻击伤害）
    defense:  int   = 2           # 防御力（受击时减免固定值）
    speed:    float = 100.0       # 移动速度（像素/秒）

    # ---- 感知属性 ----
    sight_range:   float = 180.0  # 发现玩家的距离（px）
    lose_range:    float = 240.0  # 放弃追击的距离（px）
    attack_range:  float = 36.0   # 发动攻击的距离（px）

    # ---- 巡逻属性 ----
    patrol_radius: float = 64.0   # 出生点左右巡逻半径（px）

    # ---- 种族 / 元素标签（供克制计算使用）----
    element_tags: List[str] = field(default_factory=list)
    # e.g. ["undead"]、["beast"]、["human"]、["construct"]

    # ---- 弱点 / 抗性 / 免疫（元素字符串列表）----
    weaknesses:   List[str] = field(default_factory=list)
    # e.g. ["holy", "fire"]
    resistances:  List[str] = field(default_factory=list)
    # e.g. ["dark", "poison"]
    immunities:   List[str] = field(default_factory=list)
    # e.g. ["poison"]（完全免疫，伤害归零）

    # ---- 韧性（抗硬直）—— 委托给 PoiseComponent ----
    max_poise:  float = 30.0      # 韧性上限（构造时传入 PoiseComponent）
    # 内部组件（非 dataclass 字段，__post_init__ 内创建）

    # ---- 流血触发阈值（BleedEffect 中默认 100，此处可覆盖）----
    bleed_threshold: float = 100.0

    # ---- 警戒（Alert）AI 参数 ----
    # 玩家进入视野时累积 alert_value，达到 alert_threshold 后转入 Chase
    alert_threshold: float = 0.5   # 进入 Chase 所需的警觉值（0.0~1.0）
    alert_speed:     float = 1.5   # 视野内累积速度（/秒）
    alert_decay:     float = 0.5   # 视野丢失后衰减速度（/秒）

    def __post_init__(self):
        self.hp = self.max_hp
        # 韧性组件
        self._poise = PoiseComponent(max_poise=self.max_poise)

    # ---- 数据驱动：从 dict 构造 ----

    @classmethod
    def from_dict(cls, data: dict) -> "EnemyStats":
        """
        根据 JSON 数据字典构造 EnemyStats。
        只读取已知字段，多余字段忽略，缺失字段使用类默认值。
        """
        kwargs = {}
        for f in (
            "max_hp", "atk", "defense", "speed",
            "sight_range", "lose_range", "attack_range", "patrol_radius",
            "element_tags", "weaknesses", "resistances", "immunities",
            "max_poise", "bleed_threshold",
            "alert_threshold", "alert_speed", "alert_decay",
        ):
            if f in data:
                kwargs[f] = data[f]
        return cls(**kwargs)

    # ---- HP 操作 ----

    def take_damage(self, amount: int) -> int:
        """受到伤害，返回实际扣除量（减去防御后）"""
        actual = max(0, amount - self.defense)
        actual = min(actual, self.hp)
        self.hp -= actual
        return actual

    def heal(self, amount: int) -> int:
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    # ---- 韧性操作（委托给 PoiseComponent，保留旧接口） ----

    @property
    def poise(self) -> float:
        return self._poise.poise

    @poise.setter
    def poise(self, value: float) -> None:
        self._poise.poise = max(0.0, min(value, self._poise.max_poise))

    def consume_poise(self, amount: float) -> bool:
        """
        消耗韧性，归零时返回 True（触发眩晕）。
        韧性归零后启动恢复延迟。
        """
        return self._poise.consume(amount)

    def update_poise_regen(self, dt: float, is_idle: bool) -> None:
        """每帧调用：根据脱战 / 战斗状态推进韧性恢复。"""
        self._poise.update(dt, is_idle=is_idle)

    # ---- 克制查询（供 DamageCalculator 使用）----

    def get_damage_multiplier(self, element: str) -> float:
        """
        根据元素返回受伤倍率：
          免疫 → 0.0
          抗性 → 0.5
          弱点 → 1.5
          普通 → 1.0
        """
        if element in self.immunities:
            return 0.0
        if element in self.weaknesses:
            return 1.5
        if element in self.resistances:
            return 0.5
        return 1.0
