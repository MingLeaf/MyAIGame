# =============================================================
# combat/parry_system.py —— 弹反 / 格挡系统
#
# 弹反规则（来自 game_rule.md）：
#   - 「格挡」按住时持续消耗耐力，受到伤害减免 30%~80%
#   - 「弹反」= 在格挡触发瞬间的极短「完美格挡」窗口内被攻击
#     成功触发后：玩家不受伤、敌人进入硬直、爆发高伤害
#
# 设计：
#   - BlockComponent：管理格挡按键、耐力消耗、减伤系数
#   - ParryWindow ：格挡按下瞬间打开的微小窗口（默认 0.18s）
#   - ParrySystem ：静态工具方法
#       - try_parry(player, attacker)  → bool    判定是否弹反成功
#       - resolve_parry(player, attacker)        触发弹反后效果
#
# 使用：
#   玩家在 _read_input() 中：
#       block_pressed = inp.is_pressed("block")
#       block_just    = inp.just_pressed("block")
#       self.block.update_input(block_pressed, block_just, dt)
#
#   敌人攻击命中玩家前调用：
#       if ParrySystem.try_parry(player, enemy):
#           ParrySystem.resolve_parry(player, enemy)
#           return  # 不执行受伤
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


# ---- 配置常量 ----
PARRY_WINDOW_SECONDS   = 0.18    # 弹反窗口（按下格挡后多少秒内可触发）
BLOCK_REDUCE_DEFAULT   = 0.50    # 默认格挡减伤
BLOCK_STAMINA_PER_HIT  = 25.0    # 每次受击消耗耐力
PARRY_STUN_DURATION    = 1.5     # 弹反命中敌人后的硬直时间（秒）
PARRY_DAMAGE_MULT      = 2.0     # 弹反反击伤害倍率（基于攻击方原伤害）


class ParryWindow:
    """记录弹反时间窗口的小工具（可独立使用）。"""

    def __init__(self, duration: float = PARRY_WINDOW_SECONDS):
        self._duration: float = duration
        self._timer:    float = 0.0

    def open(self) -> None:
        """打开弹反窗口（玩家刚按下格挡键时调用）。"""
        self._timer = self._duration

    def close(self) -> None:
        self._timer = 0.0

    def tick(self, dt: float) -> None:
        if self._timer > 0:
            self._timer = max(0.0, self._timer - dt)

    @property
    def is_open(self) -> bool:
        return self._timer > 0.0

    @property
    def remaining(self) -> float:
        return self._timer


class BlockComponent:
    """
    格挡组件（挂载到玩家）。

    维护：
      - 是否处于格挡状态（按住格挡键）
      - 弹反窗口（按下瞬间的极短窗口）
      - 减伤系数（盾牌 / 武器决定，默认 50%）
      - 每次受击的耐力消耗
    """

    def __init__(self,
                 reduce_ratio: float = BLOCK_REDUCE_DEFAULT,
                 stamina_per_hit: float = BLOCK_STAMINA_PER_HIT):
        self.reduce_ratio:    float = reduce_ratio
        self.stamina_per_hit: float = stamina_per_hit
        self.is_blocking:     bool  = False
        self.parry_window:    ParryWindow = ParryWindow()

    def update_input(self,
                     pressed:    bool,
                     just_pressed: bool,
                     dt:         float) -> None:
        """每帧调用：同步格挡键状态 + 推进弹反计时器。"""
        self.is_blocking = pressed
        if just_pressed:
            self.parry_window.open()
        self.parry_window.tick(dt)

    def consume_block_stamina(self, owner) -> bool:
        """
        受击时消耗耐力，返回 True 表示成功格挡，
        False 表示耐力不足→格挡破防。
        """
        stats = getattr(owner, "stats", None)
        if stats is None or not hasattr(stats, "consume_stamina"):
            return False
        return stats.consume_stamina(self.stamina_per_hit)

    def __repr__(self) -> str:
        return (f"<BlockComponent blocking={self.is_blocking} "
                f"parry_open={self.parry_window.is_open}>")


# =============================================================
# 静态工具：弹反判定 + 解算
# =============================================================

class ParrySystem:
    """无状态弹反工具集合。"""

    @staticmethod
    def try_parry(player: "Player", attacker) -> bool:
        """
        判定本次攻击是否被弹反。
        条件：
          1. 玩家挂载了 BlockComponent
          2. 弹反窗口处于打开状态
          3. 玩家面朝攻击者
        """
        block = getattr(player, "block", None)
        if not isinstance(block, BlockComponent):
            return False
        if not block.parry_window.is_open:
            return False

        # 面朝判定（攻击者在玩家正前方）
        if hasattr(player, "facing") and hasattr(attacker, "x"):
            ax = getattr(attacker, "x", 0)
            px = getattr(player,   "x", 0)
            if (ax > px and player.facing < 0) or \
               (ax < px and player.facing > 0):
                return False

        return True

    @staticmethod
    def resolve_parry(player: "Player", attacker) -> None:
        """
        弹反成功效果：
          - 关闭弹反窗口（防止单次按键多次触发）
          - 打断攻击者（切到 Hurt + 长硬直）
          - 削减攻击者韧性 / 触发眩晕
          - 反伤（PARRY_DAMAGE_MULT 倍）
          - 派发事件供 UI / 音效 / 屏幕闪光
        """
        block = getattr(player, "block", None)
        if isinstance(block, BlockComponent):
            block.parry_window.close()

        # 1. 反伤
        atk_dmg = getattr(attacker, "stats", None)
        atk_val = getattr(atk_dmg, "atk", 10) if atk_dmg else 10
        damage  = max(1, int(atk_val * PARRY_DAMAGE_MULT))

        # 击退方向：把攻击者推开
        if hasattr(attacker, "x") and hasattr(player, "x"):
            kb_dir = 1 if attacker.x > player.x else -1
        else:
            kb_dir = 1

        if hasattr(attacker, "take_damage"):
            try:
                attacker.take_damage(damage, kb_dir, poise_damage=999.0)
            except TypeError:
                attacker.take_damage(damage, kb_dir)

        # 2. 强制眩晕（额外保险，确保被打断）
        from combat.status_effect import StunEffect
        if hasattr(attacker, "status") and hasattr(attacker.status, "add"):
            attacker.status.add(StunEffect(duration=PARRY_STUN_DURATION))

        # 3. 派发事件
        event_manager.emit("player_parry", {
            "attacker": attacker,
            "damage":   damage,
        })


# 便捷工具
def try_block(player: "Player",
              raw_damage: int,
              attacker=None) -> tuple[bool, int]:
    """
    简易格挡判定：
      返回 (is_blocked, final_damage_after_block)
      - is_blocked 为 True 时已扣减相应耐力
      - 若耐力不足则 is_blocked=False, final_damage 等于原伤害
    """
    block = getattr(player, "block", None)
    if not isinstance(block, BlockComponent) or not block.is_blocking:
        return False, raw_damage

    if not block.consume_block_stamina(player):
        # 耐力不足：格挡破防（不减伤）
        return False, raw_damage

    reduced = max(1, int(raw_damage * (1.0 - block.reduce_ratio)))
    return True, reduced
