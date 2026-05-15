# =============================================================
# combat/status_manager.py —— 状态异常管理器
#
# 挂载在实体上（player.status / enemy.status）。
# 负责：添加、更新、移除 StatusEffect 实例，
#       并向 FloatingTextManager 推送异常文字。
# =============================================================
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from combat.status_effect import (
    StatusEffect,
    BleedEffect, PoisonEffect, BurnEffect, FreezeEffect,
    CurseEffect, StunEffect,
)

if TYPE_CHECKING:
    from combat.floating_text import FloatingTextManager


class StatusManager:
    """
    实体状态异常管理器。

    用法（挂载）：
        self.status = StatusManager(owner=self)

    每帧调用：
        self.status.update(dt)

    添加状态：
        self.status.add(BleedEffect())
        self.status.add(BleedEffect()); self.status.get("bleed").add_stack(30)

    取消翻滚消除的状态（如燃烧）：
        self.status.cancel_roll_removable()
    """

    def __init__(self, owner,
                 floating_text_manager: Optional["FloatingTextManager"] = None):
        self._owner  = owner
        self._ftm: Optional["FloatingTextManager"] = floating_text_manager
        self._effects: dict[str, StatusEffect] = {}

    # ----------------------------------------------------------------
    # FloatingTextManager 注入（游戏场景初始化后再绑定）
    # ----------------------------------------------------------------

    def bind_floating_text_manager(self, ftm: "FloatingTextManager") -> None:
        self._ftm = ftm

    # ----------------------------------------------------------------
    # 添加 / 查询 / 移除
    # ----------------------------------------------------------------

    def add(self, effect: StatusEffect) -> None:
        """
        添加状态。若同名状态已存在则刷新持续时间（不叠加多个实例）。

        注意：BleedEffect 的积累值不会因此被重置；
        如需重置积累值请调用 reset_bleed_stack()。
        """
        name = effect.name
        if name in self._effects:
            existing = self._effects[name]
            # 刷新持续时间（永久状态 duration=-1 时此操作无实际效果）
            if existing.duration >= 0:
                existing.elapsed  = 0.0
                existing.duration = max(existing.duration, effect.duration)
            return
        self._effects[name] = effect
        effect.apply(self._owner)
        self._push_text(f"[{name}]", _STATUS_COLOR.get(name, (220, 220, 80)))

        # 第 11 阶段：发射状态添加事件，供粒子系统订阅
        from core.event_manager import event_manager
        event_manager.emit("status_applied", {
            "entity": self._owner,
            "status": name,
        })

    def reset_bleed_stack(self) -> None:
        """将流血积累值清零（用于净化/特定道具）。"""
        bleed = self._effects.get("bleed")
        if bleed is not None and hasattr(bleed, "accumulation"):
            bleed.accumulation = 0.0

    def get(self, name: str) -> Optional[StatusEffect]:
        return self._effects.get(name)

    def has(self, name: str) -> bool:
        return name in self._effects

    def remove(self, name: str) -> None:
        if name in self._effects:
            self._effects[name].remove(self._owner)
            del self._effects[name]
            # 第 11 阶段：发射状态移除事件，供粒子系统清理
            from core.event_manager import event_manager
            event_manager.emit("status_removed", {
                "entity": self._owner,
                "status": name,
            })

    def clear(self) -> None:
        """移除所有状态"""
        for eff in list(self._effects.values()):
            eff.remove(self._owner)
        self._effects.clear()

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        to_remove = []
        for name, eff in self._effects.items():
            alive = eff.update(dt, self._owner)
            if not alive:
                to_remove.append(name)
        for name in to_remove:
            self._effects[name].remove(self._owner)
            del self._effects[name]

    # ----------------------------------------------------------------
    # 翻滚消除（燃烧等可被翻滚清除的状态）
    # ----------------------------------------------------------------

    def cancel_roll_removable(self) -> None:
        """玩家执行翻滚时调用，消除可翻滚清除的状态（如 BurnEffect）。"""
        for eff in list(self._effects.values()):
            if hasattr(eff, "cancel_by_roll"):
                eff.cancel_by_roll()

    # ----------------------------------------------------------------
    # 冻结增伤接口（供 DamageCalculator 查询）
    # ----------------------------------------------------------------

    def frozen_damage_bonus(self) -> float:
        """若当前处于冰冻状态，返回额外伤害系数（1.20）；否则返回 1.0。"""
        if self.has("freeze"):
            from combat.status_effect import FreezeEffect
            return 1.0 + FreezeEffect.EXTRA_DMG_BONUS
        return 1.0

    # ----------------------------------------------------------------
    # 内部工具
    # ----------------------------------------------------------------

    def _push_text(self, text: str, color: tuple) -> None:
        """向 FloatingTextManager 推送状态文字（若已绑定）。"""
        if self._ftm is None:
            return
        owner = self._owner
        # 尝试从 owner 获取世界坐标
        if hasattr(owner, "rect"):
            wx = owner.rect.centerx
            wy = owner.rect.top
        elif hasattr(owner, "x") and hasattr(owner, "y"):
            wx, wy = int(owner.x), int(owner.y)
        else:
            return
        self._ftm.add(text, wx, wy, color=color, size=14)

    # ----------------------------------------------------------------
    # 便捷属性
    # ----------------------------------------------------------------

    @property
    def is_frozen(self) -> bool:
        return self.has("freeze")

    @property
    def is_stunned(self) -> bool:
        return self.has("stun")

    @property
    def is_burning(self) -> bool:
        return self.has("burn")

    @property
    def active_names(self) -> list[str]:
        return list(self._effects.keys())

    def __repr__(self) -> str:
        return f"<StatusManager effects={self.active_names}>"


# ----------------------------------------------------------------
# 状态文字颜色表
# ----------------------------------------------------------------
_STATUS_COLOR: dict[str, tuple] = {
    "bleed":  (220,  30,  30),
    "poison": ( 60, 200,  60),
    "burn":   (255, 120,  30),
    "freeze": (100, 200, 255),
    "curse":  (160,  40, 220),
    "stun":   (255, 230,  60),
}
