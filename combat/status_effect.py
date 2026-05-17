# =============================================================
# combat/status_effect.py —— 状态异常基类 + 各种异常实现
#
# 状态异常说明（来自 game_rule.md）：
#   流血：累积值达阈值 → 爆发扣当前HP的15%
#   中毒：持续扣血30s
#   燃烧：持续扣血 + 降防御，可翻滚消除
#   冰冻：硬直2s + 额外20%伤害
#   诅咒：最大HP减半
#   眩晕：韧性被打空，可被处决
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass  # 避免循环导入，owner 用 Any 鸭子类型


# ============================================================
# 数据驱动：从 data/balance/status_effect_values.json 加载
# ============================================================

def _load_balance_values() -> dict:
    """加载状态异常数值配置；失败时返回空 dict（使用类常量兜底）。"""
    try:
        from utils.json_loader import load_from_data_dir
        return load_from_data_dir("balance/status_effect_values.json")
    except Exception:
        return {}


_BALANCE = _load_balance_values()


# ============================================================
# 基类
# ============================================================

class StatusEffect:
    """
    状态异常基类。

    生命周期：
        apply(owner)   —— 挂载时调用一次，可修改属性
        update(dt, owner) —— 每帧调用，返回 True 表示仍然存活
        remove(owner)  —— 到期或主动移除时调用一次，还原属性

    子类可选覆盖 apply / remove；必须实现 update 内部逻辑。
    """

    #: 状态唯一名称，供 StatusManager 查重
    name: str = "base"
    #: 状态图标颜色（用于 HUD 小图标）
    color: tuple = (200, 200, 200)

    def __init__(self, duration: float = 5.0):
        self.duration:  float = duration    # 剩余持续时间（秒），-1 为永久
        self.elapsed:   float = 0.0         # 已经过时间

    # ----------------------------------------------------------------

    @property
    def is_permanent(self) -> bool:
        return self.duration < 0

    @property
    def expired(self) -> bool:
        return (not self.is_permanent) and (self.elapsed >= self.duration)

    # ----------------------------------------------------------------

    def apply(self, owner) -> None:
        """挂载时执行一次性效果（如降防御、减最大HP）。子类按需重写。"""
        pass

    def remove(self, owner) -> None:
        """移除时还原效果。子类按需重写。"""
        pass

    def update(self, dt: float, owner) -> bool:
        """
        每帧更新。
        返回 True：效果仍存活。
        返回 False：效果到期，StatusManager 将调用 remove 并销毁。
        """
        if not self.is_permanent:
            self.elapsed += dt
        return not self.expired

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} duration={self.duration:.1f}s elapsed={self.elapsed:.1f}s>"


# ============================================================
# 流血（Bleed）
# ============================================================

class BleedEffect(StatusEffect):
    """
    流血：积累值达到阈值后，爆发扣当前HP 15%。
    每次叠加调用 add_stack(amount) 增加积累值。
    """

    name  = "bleed"
    color = (200, 30, 30)

    # 默认值，会在导入时被 _BALANCE["bleed"] 覆盖
    THRESHOLD    = 100.0
    BURST_RATIO  = 0.15
    DECAY_RATE   = 8.0

    def __init__(self):
        super().__init__(duration=-1)   # 永久存活，由 StatusManager 控制
        self.accumulation: float = 0.0
        self._burst_timer: float = 0.0  # 爆发后的短暂冷却（防止多帧连续爆发）

    def add_stack(self, amount: float) -> None:
        self.accumulation += amount

    def update(self, dt: float, owner) -> bool:
        # 优先读取 owner.stats.bleed_threshold，兜底类常量 THRESHOLD
        threshold = self.THRESHOLD
        if hasattr(owner, "stats") and hasattr(owner.stats, "bleed_threshold"):
            threshold = owner.stats.bleed_threshold

        # 爆发检测
        if self.accumulation >= threshold:
            current_hp = getattr(owner.stats, "hp", 1) if hasattr(owner, "stats") else 1
            burst_dmg  = max(1, int(current_hp * self.BURST_RATIO))
            if hasattr(owner, "stats") and hasattr(owner.stats, "take_damage"):
                owner.stats.take_damage(burst_dmg)
            self.accumulation = 0.0
            # 触发飘字回调（由 StatusManager 负责）
            if hasattr(owner, "_on_bleed_burst"):
                owner._on_bleed_burst(burst_dmg)

        # 自然衰减
        self.accumulation = max(0.0, self.accumulation - self.DECAY_RATE * dt)

        # 积累归零后移除
        return self.accumulation > 0.0


# ============================================================
# 中毒（Poison）
# ============================================================

class PoisonEffect(StatusEffect):
    """中毒：持续 30s，每秒扣固定伤害。支持积累阈值。"""

    name  = "poison"
    color = (80, 200, 80)

    # 默认值，会被 _BALANCE["poison"] 覆盖
    DAMAGE_PER_SEC   = 3.0
    DEFAULT_DURATION = 30.0
    THRESHOLD        = 80.0       # 积累阈值，达到后才生效

    def __init__(self, damage_per_sec: float = DAMAGE_PER_SEC,
                 duration: float = DEFAULT_DURATION):
        super().__init__(duration=duration)
        self.damage_per_sec = damage_per_sec
        self.accumulation: float = 0.0
        self._tick_timer: float = 0.0
        self._triggered: bool = False   # 是否已达到阈值开始生效

    def add_stack(self, amount: float) -> None:
        """积累中毒值。"""
        self.accumulation += amount

    def update(self, dt: float, owner) -> bool:
        self.elapsed += dt

        # 未达到阈值：仅衰减积累值，不扣血
        if not self._triggered:
            self.accumulation = max(0.0, self.accumulation - 3.0 * dt)
            if self.accumulation >= self.THRESHOLD:
                self._triggered = True
            return True

        self._tick_timer += dt
        if self._tick_timer >= 1.0:
            self._tick_timer -= 1.0
            dmg = max(1, int(self.damage_per_sec))
            # 第 11 阶段：通过 owner.take_damage（而非 stats.take_damage）确保死亡流程触发
            if hasattr(owner, "take_damage"):
                try:
                    owner.take_damage(dmg)
                except Exception:
                    if hasattr(owner, "stats") and hasattr(owner.stats, "take_damage"):
                        owner.stats.take_damage(dmg)
            if hasattr(owner, "_on_dot_damage"):
                owner._on_dot_damage(dmg, "poison")
        return not self.expired


# ============================================================
# 燃烧（Burn）
# ============================================================

class BurnEffect(StatusEffect):
    """
    燃烧：持续扣血 + 降低防御。
    翻滚可提前消除（由外部逻辑调用 cancel_by_roll()）。
    """

    name  = "burn"
    color = (255, 120, 30)

    # 默认值，会被 _BALANCE["burn"] 覆盖
    DAMAGE_PER_SEC   = 5.0
    DEFENSE_PENALTY  = 3
    DEFAULT_DURATION = 8.0

    def __init__(self, damage_per_sec: float = DAMAGE_PER_SEC,
                 duration: float = DEFAULT_DURATION):
        super().__init__(duration=duration)
        self.damage_per_sec    = damage_per_sec
        self._defense_applied  = False
        self._tick_timer: float = 0.0
        self._cancelled: bool   = False

    def apply(self, owner) -> None:
        """降低防御"""
        if hasattr(owner, "stats") and hasattr(owner.stats, "defense"):
            owner.stats.defense = max(0, owner.stats.defense - self.DEFENSE_PENALTY)
            self._defense_applied = True

    def remove(self, owner) -> None:
        """还原防御"""
        if self._defense_applied and hasattr(owner, "stats") \
                and hasattr(owner.stats, "defense"):
            owner.stats.defense += self.DEFENSE_PENALTY
            self._defense_applied = False

    def cancel_by_roll(self) -> None:
        """翻滚消除：标记为立即到期"""
        self._cancelled = True

    def update(self, dt: float, owner) -> bool:
        if self._cancelled:
            return False

        self.elapsed += dt
        self._tick_timer += dt
        if self._tick_timer >= 1.0:
            self._tick_timer -= 1.0
            dmg = max(1, int(self.damage_per_sec))
            if hasattr(owner, "take_damage"):
                try:
                    owner.take_damage(dmg)
                except Exception:
                    if hasattr(owner, "stats") and hasattr(owner.stats, "take_damage"):
                        owner.stats.take_damage(dmg)
            if hasattr(owner, "_on_dot_damage"):
                owner._on_dot_damage(dmg, "burn")
        return not self.expired


# ============================================================
# 冰冻（Freeze）
# ============================================================

class FreezeEffect(StatusEffect):
    """
    冰冻：硬直 2s，期间受到额外 20% 伤害。
    通过设置 owner.frozen = True / False 控制移动锁定。
    """

    name  = "freeze"
    color = (100, 200, 255)

    # 默认值，会被 _BALANCE["freeze"] 覆盖
    DEFAULT_DURATION  = 2.0
    EXTRA_DMG_BONUS   = 0.20

    def __init__(self, duration: float = DEFAULT_DURATION):
        super().__init__(duration=duration)

    def apply(self, owner) -> None:
        owner.frozen = True

    def remove(self, owner) -> None:
        owner.frozen = False

    def update(self, dt: float, owner) -> bool:
        self.elapsed += dt
        return not self.expired


# ============================================================
# 诅咒（Curse）—— 最大HP减半
# ============================================================

class CurseEffect(StatusEffect):
    """诅咒：最大HP减半（永久直到被净化）。"""

    name  = "curse"
    color = (140, 40, 200)

    def __init__(self, duration: float = -1.0):
        super().__init__(duration=duration)
        self._original_max_hp: Optional[int] = None

    def apply(self, owner) -> None:
        if hasattr(owner, "stats") and hasattr(owner.stats, "max_hp"):
            self._original_max_hp = owner.stats.max_hp
            owner.stats.max_hp    = max(1, owner.stats.max_hp // 2)
            # 当前HP也不能超过新的上限
            owner.stats.hp        = min(owner.stats.hp, owner.stats.max_hp)

    def remove(self, owner) -> None:
        if self._original_max_hp is not None and \
                hasattr(owner, "stats") and hasattr(owner.stats, "max_hp"):
            owner.stats.max_hp    = self._original_max_hp
            self._original_max_hp = None


# ============================================================
# 眩晕（Stun）—— 韧性被打空
# ============================================================

class StunEffect(StatusEffect):
    """眩晕：韧性归零，可被处决。"""

    name  = "stun"
    color = (255, 230, 60)

    # 默认值，会被 _BALANCE["stun"] 覆盖
    DEFAULT_DURATION = 2.0

    def __init__(self, duration: float = DEFAULT_DURATION):
        super().__init__(duration=duration)

    def apply(self, owner) -> None:
        owner.stunned = True

    def remove(self, owner) -> None:
        owner.stunned = False

    def update(self, dt: float, owner) -> bool:
        self.elapsed += dt
        return not self.expired


# ============================================================
# 应用 JSON 配置覆盖类常量（必须在所有类定义之后调用）
# ============================================================

def _apply_balance_overrides() -> None:
    """将 _BALANCE 中的字段写入对应类常量，实现数据驱动。"""
    if not _BALANCE:
        return

    bleed = _BALANCE.get("bleed", {})
    if bleed:
        BleedEffect.THRESHOLD   = float(bleed.get("threshold",   BleedEffect.THRESHOLD))
        BleedEffect.BURST_RATIO = float(bleed.get("burst_ratio", BleedEffect.BURST_RATIO))
        BleedEffect.DECAY_RATE  = float(bleed.get("decay_rate",  BleedEffect.DECAY_RATE))

    poison = _BALANCE.get("poison", {})
    if poison:
        PoisonEffect.DAMAGE_PER_SEC   = float(poison.get("damage_per_sec",
                                                         PoisonEffect.DAMAGE_PER_SEC))
        PoisonEffect.DEFAULT_DURATION = float(poison.get("duration",
                                                         PoisonEffect.DEFAULT_DURATION))

    burn = _BALANCE.get("burn", {})
    if burn:
        BurnEffect.DAMAGE_PER_SEC   = float(burn.get("damage_per_sec",
                                                     BurnEffect.DAMAGE_PER_SEC))
        BurnEffect.DEFENSE_PENALTY  = int(burn.get("defense_penalty",
                                                   BurnEffect.DEFENSE_PENALTY))
        BurnEffect.DEFAULT_DURATION = float(burn.get("duration",
                                                     BurnEffect.DEFAULT_DURATION))

    freeze = _BALANCE.get("freeze", {})
    if freeze:
        FreezeEffect.DEFAULT_DURATION = float(freeze.get("duration",
                                                         FreezeEffect.DEFAULT_DURATION))
        FreezeEffect.EXTRA_DMG_BONUS  = float(freeze.get("extra_dmg_bonus",
                                                         FreezeEffect.EXTRA_DMG_BONUS))

    stun = _BALANCE.get("stun", {})
    if stun:
        StunEffect.DEFAULT_DURATION = float(stun.get("duration",
                                                     StunEffect.DEFAULT_DURATION))


_apply_balance_overrides()