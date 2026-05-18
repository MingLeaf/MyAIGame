# =============================================================
# combat/poise_system.py —— 韧性 / 抗硬直系统
#
# 韧性规则（来自 game_rule.md）：
#   - 每次受击消耗韧性，同时重置恢复延迟
#   - 韧性归零 → 触发硬直（眩晕），可被处决
#   - 未受伤害 5 秒后开始恢复韧性
#   - 眩晕结束后韧性立即回满
#
# 设计：
#   将原本嵌入 EnemyStats 的韧性逻辑独立为 PoiseComponent，
#   既可用于敌人也可挂载到玩家（重甲套装提供韧性），
#   EnemyStats 内部转为对此组件的薄包装以保持兼容。
# =============================================================
from __future__ import annotations


# 默认参数
DEFAULT_MAX_POISE      = 30.0
DEFAULT_REGEN_DELAY    = 5.0     # 未受伤害后开始恢复的延迟（秒）
DEFAULT_REGEN_RATE     = 10.0    # 战斗中每秒回复量
INSTANT_RESTORE_IDLE   = True    # 脱战是否立即回满


class PoiseComponent:
    """
    韧性组件。

    用法：
        self.poise = PoiseComponent(max_poise=30.0)

        # 受击时
        broken = self.poise.consume(15.0)   # 返回 True 表示韧性击破

        # 每帧
        self.poise.update(dt, is_idle=self.fsm.is_in("Idle"))

        # 眩晕结束时
        self.poise.full_restore()
    """

    def __init__(self,
                 max_poise:  float = DEFAULT_MAX_POISE,
                 regen_delay: float = DEFAULT_REGEN_DELAY,
                 regen_rate:  float = DEFAULT_REGEN_RATE):
        self.max_poise:        float = max_poise
        self.poise:            float = max_poise
        self.regen_delay:      float = regen_delay
        self.regen_rate:       float = regen_rate
        self._regen_timer:     float = 0.0   # 距下次开始回复的剩余时间

    # ----------------------------------------------------------------
    # 接口
    # ----------------------------------------------------------------

    def consume(self, amount: float) -> bool:
        """
        消耗韧性。每次受击都重置恢复延迟。
        返回 True 表示击破（归零）。
        """
        if amount <= 0 or self.max_poise <= 0:
            return False
        self.poise = max(0.0, self.poise - amount)
        # 每次受击都重置恢复延迟（5秒不受击才开始恢复）
        self._regen_timer = self.regen_delay
        if self.poise <= 0:
            return True
        return False

    def update(self, dt: float, is_idle: bool = False) -> None:
        """
        每帧更新韧性恢复。
        :param is_idle: True 表示实体处于脱战状态，可立即回满
        """
        if self.poise >= self.max_poise:
            return

        # 恢复延迟倒计时（未受伤害 5 秒后才开始回复）
        if self._regen_timer > 0.0:
            self._regen_timer -= dt
            return

        if is_idle and INSTANT_RESTORE_IDLE:
            self.poise = self.max_poise
        else:
            self.poise = min(self.max_poise,
                             self.poise + self.regen_rate * dt)

    def full_restore(self) -> None:
        """眩晕结束后立即回满韧性。"""
        self.poise = self.max_poise
        self._regen_timer = 0.0

    def reset(self) -> None:
        """立即回满（如复活）。"""
        self.poise = self.max_poise
        self._regen_timer = 0.0

    def set_max(self, new_max: float) -> None:
        """运行时调整韧性上限（如装备护甲）。"""
        if new_max <= 0:
            new_max = 0.0
        ratio = self.poise / self.max_poise if self.max_poise > 0 else 1.0
        self.max_poise = new_max
        self.poise     = new_max * ratio

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    @property
    def ratio(self) -> float:
        return self.poise / self.max_poise if self.max_poise > 0 else 0.0

    @property
    def is_broken(self) -> bool:
        return self.poise <= 0

    @property
    def is_recovering(self) -> bool:
        """是否正在延迟等待中（未开始恢复）"""
        return self._regen_timer > 0.0

    def __repr__(self) -> str:
        return (f"<PoiseComponent {self.poise:.1f}/{self.max_poise:.1f} "
                f"timer={self._regen_timer:.2f}>")
