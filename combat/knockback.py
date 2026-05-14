# =============================================================
# combat/knockback.py —— 击退物理系统
#
# 设计：
#   1. 击退本质是「短时强制位移 + 指数衰减」
#   2. KnockbackComponent 封装速度持有 + 衰减 + 取出
#   3. 实体在物理解算前先调用 component.consume() 拿到 vel_x 覆盖到自身 vel_x
#   4. apply() 设置初始速度，随时间衰减到 0 后停止
#
# 用法：
#   self.kb = KnockbackComponent()
#
#   # 受击时
#   self.kb.apply(direction=+1, force=200.0)
#
#   # 每帧物理前
#   vx = self.kb.consume(dt)
#   if vx != 0:
#       self.vel_x = vx
# =============================================================
from __future__ import annotations


# 默认衰减系数（指数衰减：vel *= (1 - DECAY_RATE * dt)）
DEFAULT_DECAY_RATE = 8.0

# 速度低于该阈值时直接归零，避免无限小数游走
STOP_THRESHOLD = 1.0


class KnockbackComponent:
    """
    击退组件。
    - apply(dir, force) 设置初速度（+1 向右 / -1 向左）
    - consume(dt) 每帧取出当前速度（同时进行指数衰减）
    - is_active 判断是否仍在击退过程中
    """

    def __init__(self,
                 decay_rate:    float = DEFAULT_DECAY_RATE,
                 stop_threshold: float = STOP_THRESHOLD):
        self._vx:           float = 0.0
        self._decay_rate:   float = decay_rate
        self._stop_threshold: float = stop_threshold

    # ----------------------------------------------------------------
    # 接口
    # ----------------------------------------------------------------

    def apply(self, direction: int, force: float) -> None:
        """
        施加击退。
        :param direction: +1 向右 / -1 向左 / 0 无方向
        :param force:     初速度（绝对值）
        """
        if direction == 0 or force <= 0:
            return
        # 取较大值（避免被弱击退覆盖强击退）
        target = direction * abs(force)
        if abs(target) > abs(self._vx):
            self._vx = target

    def consume(self, dt: float) -> float:
        """
        取出本帧的击退速度（同时衰减）。
        若已结束则返回 0.0。
        """
        if self._vx == 0.0:
            return 0.0
        cur = self._vx
        # 指数衰减
        self._vx *= max(0.0, 1.0 - self._decay_rate * dt)
        if abs(self._vx) < self._stop_threshold:
            self._vx = 0.0
        return cur

    def reset(self) -> None:
        """立即清除击退（如死亡时）。"""
        self._vx = 0.0

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._vx != 0.0

    @property
    def velocity(self) -> float:
        """只读当前速度（不消费）。"""
        return self._vx

    def __repr__(self) -> str:
        return f"<KnockbackComponent vx={self._vx:.1f}>"


# ----------------------------------------------------------------
# 工具函数：直接施加到拥有 .kb 组件的实体（语法糖）
# ----------------------------------------------------------------

def apply_knockback(target, direction: int, force: float) -> bool:
    """
    便捷函数：若 target 拥有 KnockbackComponent（属性名 `kb`）则施加击退，
    否则尝试写入 `_knockback_vx` 兼容字段。
    返回 True 表示成功施加。
    """
    if direction == 0 or force <= 0:
        return False
    kb = getattr(target, "kb", None)
    if isinstance(kb, KnockbackComponent):
        kb.apply(direction, force)
        return True
    # 兼容旧字段
    if hasattr(target, "_knockback_vx"):
        target._knockback_vx = direction * abs(force)
        return True
    return False
