# =============================================================
# utils/timer.py —— 计时器工具
# =============================================================


class Timer:
    """
    通用倒计时器。
    每帧调用 update(dt)，通过 is_finished() 判断是否完成。
    """

    def __init__(self, duration: float, auto_reset: bool = False):
        """
        :param duration:   持续时间（秒）
        :param auto_reset: 到期后是否自动重置
        """
        self._duration   = duration
        self._elapsed    = 0.0
        self._running    = False
        self._auto_reset = auto_reset
        self._finished   = False

    # ---- 控制 ----

    def start(self):
        """启动（重置并开始计时）"""
        self._elapsed  = 0.0
        self._running  = True
        self._finished = False

    def stop(self):
        """停止计时"""
        self._running = False

    def reset(self):
        """重置到初始状态（不自动开始）"""
        self._elapsed  = 0.0
        self._running  = False
        self._finished = False

    def restart(self):
        """立即重新开始"""
        self.start()

    # ---- 更新 ----

    def update(self, dt: float):
        """每帧调用，dt 单位：秒"""
        if not self._running:
            return
        self._elapsed += dt
        if self._elapsed >= self._duration:
            self._elapsed  = self._duration
            self._finished = True
            if self._auto_reset:
                self.start()
            else:
                self._running = False

    # ---- 查询 ----

    def is_running(self) -> bool:
        return self._running

    def is_finished(self) -> bool:
        """到期时返回 True，仅在 auto_reset=False 时保持 True"""
        return self._finished

    def progress(self) -> float:
        """已过时间占总时长的比例 [0.0, 1.0]"""
        if self._duration <= 0:
            return 1.0
        return min(self._elapsed / self._duration, 1.0)

    def remaining(self) -> float:
        """剩余时间（秒）"""
        return max(0.0, self._duration - self._elapsed)

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float):
        self._duration = value


class Cooldown(Timer):
    """
    技能冷却计时器：到期后保持 ready 状态，直到被再次触发。
    """

    def __init__(self, duration: float):
        super().__init__(duration, auto_reset=False)
        self._elapsed  = duration   # 初始视为已冷却完毕（即可立刻使用）
        self._finished = True

    def is_ready(self) -> bool:
        """是否可以使用（冷却完成）"""
        return not self._running

    def trigger(self) -> bool:
        """尝试触发；如果 ready 则启动冷却并返回 True，否则返回 False"""
        if self.is_ready():
            self.start()
            return True
        return False
