# =============================================================
# physics/gravity.py —— 重力系统（控制跳跃和坠落）
# =============================================================

from config import GRAVITY, MAX_FALL_SPEED, JUMP_FORCE
from utils.math_utils import clamp


class GravitySystem:
    """
    重力模拟器，挂载在需要受重力影响的实体上。
    每帧调用 apply(dt) 更新 vel_y。
    """

    def __init__(self,
                 gravity: float     = GRAVITY,
                 max_fall: float    = MAX_FALL_SPEED,
                 jump_force: float  = JUMP_FORCE):
        self._gravity   = gravity
        self._max_fall  = max_fall
        self._jump_force= jump_force

        self.vel_y:     float = 0.0
        self.on_ground: bool  = False
        self._can_jump: bool  = True
        self._in_water: bool  = False   # 水中减慢下落

    def accumulate(self, dt: float):
        """
        仅累积重力加速度，不检测地面，不修改位置。
        用于「先重力→再解算→再同步 on_ground」的流程。
        只在空中时调用（在地面时忽略）。
        """
        if not self.on_ground:
            g = self._gravity * (0.4 if self._in_water else 1.0)
            self.vel_y += g * dt
            self.vel_y  = min(self.vel_y, self._max_fall)

    # ---- 每帧更新 ----

    def apply(self, dt: float) -> float:
        """
        应用重力，更新 vel_y。
        返回本帧 Y 轴位移（像素）。
        """
        if self.on_ground:
            # 在地面上：归零下落速度，保留微小贴地速度防止抖动
            if self.vel_y > 0:
                self.vel_y = 0.0
            self._can_jump = True
        else:
            g = self._gravity * (0.4 if self._in_water else 1.0)
            self.vel_y += g * dt
            self.vel_y  = min(self.vel_y, self._max_fall)

        return self.vel_y * dt

    # ---- 跳跃 ----

    def jump(self, force_multiplier: float = 1.0) -> bool:
        """
        触发跳跃。
        :param force_multiplier: 跳跃力倍率
        :return: True = 成功跳跃
        """
        if not self._can_jump:
            return False
        self.vel_y    = self._jump_force * force_multiplier
        self.on_ground = False
        self._can_jump = False
        return True

    def force_jump(self, vel: float):
        """强制设置跳跃速度（弹射台 / 特殊技能）"""
        self.vel_y = vel
        self.on_ground = False

    # ---- 状态控制 ----

    def set_on_ground(self, value: bool):
        self.on_ground = value
        if value:
            self._can_jump = True
            if self.vel_y > 0:
                self.vel_y = 0.0

    def enter_water(self):
        self._in_water = True
        self._max_fall = MAX_FALL_SPEED * 0.4

    def exit_water(self):
        self._in_water = False
        self._max_fall = MAX_FALL_SPEED

    def reset(self):
        self.vel_y     = 0.0
        self.on_ground = False
        self._can_jump = True
        self._in_water = False

    # ---- 属性 ----

    @property
    def is_falling(self) -> bool:
        return self.vel_y > 50   # 下落速度大于 50px/s 才算"下落中"

    @property
    def is_rising(self) -> bool:
        return self.vel_y < 0

    @property
    def can_jump(self) -> bool:
        return self._can_jump
