# =============================================================
# weapons/weapon_art.py —— 战技系统基类
#
# 战技触发流程（U 键 / input_handler.weapon_art）：
#   1. PlayerCombat 检测到 weapon_art 输入
#   2. 取出 player.weapon.get_weapon_art() → WeaponArt 实例
#   3. 调用 art.try_execute(player, area) → bool
#       - 检查冷却 / 灵力 / 弹药 / 状态前置
#       - 扣除资源
#       - 调用 _execute(player, area) 执行实际逻辑（生成抛射物 / 大范围判定 / 治疗 ...）
#       - 派发 weapon_art_used 事件
#
# 子类可重写 _execute 实现具体效果，
# 也可重写 _check_resources 自定义资源消耗（如 BowArt 需要箭矢）。
# =============================================================
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


class WeaponArt:
    """
    战技基类。
    """

    #: 唯一 ID（如 "spear_counter"）
    art_id:        str   = "art"
    #: 中文显示名
    display_name:  str   = "战技"
    #: 灵力（mana）消耗
    mana_cost:     int   = 20
    #: 冷却（秒）
    cooldown:      float = 1.5
    #: 韧性伤害基础（用于战技命中扣韧）
    poise_damage:  float = 20.0
    #: 描述（UI 用）
    description:   str   = ""

    def __init__(self):
        self._cd_timer: float = 0.0   # 当前冷却剩余

    # ----------------------------------------------------------------
    # 每帧推进（由 PlayerCombat.update 驱动）
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self._cd_timer > 0.0:
            self._cd_timer = max(0.0, self._cd_timer - dt)

    # ----------------------------------------------------------------
    # 触发入口
    # ----------------------------------------------------------------

    def try_execute(self, player: "Player", area=None) -> bool:
        """
        尝试触发战技。
        :return: True 表示触发成功（已扣资源），False 表示前置不满足。
        """
        # 1. 冷却检查
        if self._cd_timer > 0.0:
            return False

        # 2. 资源检查（灵力 / 弹药 / 自定义）
        if not self._check_resources(player):
            return False

        # 3. 扣除资源
        self._consume_resources(player)

        # 4. 执行
        try:
            self._execute(player, area)
        except Exception as exc:
            # 执行异常仍记冷却避免疯狂重试
            import logging
            logging.getLogger(__name__).exception(
                "WeaponArt[%s] _execute 异常: %s", self.art_id, exc)

        # 5. 进入冷却
        self._cd_timer = self.cooldown

        # 6. 事件
        event_manager.emit("weapon_art_used", {
            "art_id":       self.art_id,
            "display_name": self.display_name,
            "player":       player,
        })
        return True

    # ----------------------------------------------------------------
    # 子类可重写的钩子
    # ----------------------------------------------------------------

    def _check_resources(self, player: "Player") -> bool:
        """检查灵力是否充足。子类可叠加额外检查（如箭矢数量）。"""
        if self.mana_cost <= 0:
            return True
        stats = getattr(player, "stats", None)
        if stats is None:
            return False
        return getattr(stats, "mana", 0) >= self.mana_cost

    def _consume_resources(self, player: "Player") -> None:
        """扣除灵力。子类可叠加扣箭矢等。"""
        if self.mana_cost > 0 and hasattr(player, "stats"):
            try:
                player.stats.consume_mana(self.mana_cost)
            except Exception:
                pass

    def _execute(self, player: "Player", area) -> None:
        """
        子类必须实现：战技实际效果。
        通常会做以下事情之一：
          - 创建一个超大判定框（近战范围战技）
          - 生成 Projectile / MagicBall / Arrow 推入 area.projectiles
          - 治疗 / 加 buff
        """
        pass

    # ----------------------------------------------------------------
    # 状态查询
    # ----------------------------------------------------------------

    @property
    def cd_remaining(self) -> float:
        return self._cd_timer

    @property
    def is_ready(self) -> bool:
        return self._cd_timer <= 0.0

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} {self.art_id} "
                f"mana={self.mana_cost} cd={self.cooldown}s>")
