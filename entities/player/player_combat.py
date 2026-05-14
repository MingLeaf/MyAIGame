# =============================================================
# entities/player/player_combat.py —— 玩家战斗组件
#
# 设计目标：
#   把原本散落在 player.py / player_states.py 中的战斗细节
#   （受击/格挡/弹反/无敌帧/击退）抽出，统一通过本组件暴露接口。
#   Player 持有 `self.combat: PlayerCombat`，外部统一调用：
#       player.combat.take_damage(...)
#       player.combat.try_parry(attacker)
#       player.combat.try_block(damage)
#
#   旧接口 player.take_damage() 仍保留（内部转发到本组件），
#   保证敌人 AI 的攻击代码无需改动。
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from combat.parry_system import (
    BlockComponent, ParrySystem, try_block as try_block_func,
)
from combat.knockback   import KnockbackComponent
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


# 受击硬直时间（秒）
HURT_STAGGER_DEFAULT = 0.30
# 受击时的击退力（敌人弱攻击）
HURT_KNOCKBACK_FORCE = 200.0


class PlayerCombat:
    """
    玩家战斗组件。

    负责：
      - take_damage(amount, knockback_dir, attacker=None)
      - 弹反检测：先 try_parry，命中 → 反伤敌人 + 自身免伤
      - 格挡减伤：BlockComponent 配合
      - 无敌帧：翻滚状态下无视伤害
      - 击退：通过 KnockbackComponent
      - 受击事件：派发 player_hurt / player_death
    """

    def __init__(self, player: "Player"):
        self.player: "Player" = player

        # 子组件（玩家可在外部直接访问）
        self.block: BlockComponent       = BlockComponent()
        self.kb:    KnockbackComponent   = KnockbackComponent()

        # 受击硬直计时
        self.hurt_stagger: float = HURT_STAGGER_DEFAULT

    # ----------------------------------------------------------------
    # 每帧更新（由 Player.update 驱动）
    # ----------------------------------------------------------------

    def update(self, dt: float, block_pressed: bool, block_just: bool) -> None:
        """同步格挡输入 + 推进弹反窗口 + 推进战技冷却。"""
        self.block.update_input(block_pressed, block_just, dt)
        # 推进当前武器战技的冷却
        weapon = getattr(self.player, "weapon", None)
        if weapon is not None:
            art = None
            try:
                art = weapon.get_weapon_art()
            except Exception:
                art = None
            if art is not None:
                art.update(dt)

    # ----------------------------------------------------------------
    # 战技触发（U 键）
    # ----------------------------------------------------------------

    def try_weapon_art(self, area=None) -> bool:
        """
        尝试触发当前武器的战技。
        :param area: 当前所在区域（用于战技生成抛射物）。可为 None。
        :return: True 表示触发成功；False 表示无战技 / 冷却中 / 资源不足。
        """
        p = self.player
        # 死亡 / 受击 / 翻滚 期间不触发
        if p.fsm.is_in("Dead", "Hurt", "Roll"):
            return False
        weapon = getattr(p, "weapon", None)
        if weapon is None:
            return False
        try:
            art = weapon.get_weapon_art()
        except Exception:
            return False
        if art is None:
            return False
        return art.try_execute(p, area)

    # ----------------------------------------------------------------
    # 受击主入口
    # ----------------------------------------------------------------

    def take_damage(self,
                    amount: int,
                    knockback_dir: int = 0,
                    attacker=None,
                    *,
                    element: str = "physical",
                    poise_damage: float = 10.0) -> int:
        """
        统一受击入口。
        :param amount:        攻击者原始伤害
        :param knockback_dir: 击退方向 (+1 / -1 / 0)
        :param attacker:      攻击者引用（用于弹反 / 格挡）
        :param element:       攻击元素（影响走护甲防御 OR 魔法抗性）
        :param poise_damage:  对玩家韧性的伤害（暂保留，后续阶段对接 PoiseComponent）
        :return: 实际扣除的 HP（0 表示完全免伤）

        受击伤害公式（第 7 阶段补丁后）：
            after_armor = raw - armor_defense * DEFENSE_COEFF
            after_set   = after_armor * (1 - def_bonus_pct)   # 套装百分比减伤
            final       = max(MIN_DAMAGE, after_set)
        弹反 / 翻滚无敌帧 仍优先生效。
        """
        p = self.player

        # 0. 调试模式：上帝模式无敌
        import utils.debug as dbg
        if dbg.enabled and dbg.god_mode:
            return 0

        # 1. 死亡 / 无敌帧
        if p.fsm.is_in("Dead"):
            return 0
        if getattr(p, "invincible", False):
            event_manager.emit("player_dodge", {"attacker": attacker})
            return 0

        # 2. 弹反优先
        if attacker is not None and ParrySystem.try_parry(p, attacker):
            ParrySystem.resolve_parry(p, attacker)
            return 0

        # 3. 格挡减伤（先调用 try_block 计算被格挡后的伤害量）
        is_blocked, blocked_dmg = try_block_func(p, amount, attacker)
        if is_blocked:
            # 格挡命中：不进入硬直，但可能轻微击退；护甲再吃一道减伤
            if knockback_dir != 0:
                self.kb.apply(knockback_dir, HURT_KNOCKBACK_FORCE * 0.4)
            final, actual = p.stats.take_damage_with_defense(
                blocked_dmg, element=element)
            event_manager.emit("player_block_hit", {
                "damage": actual, "raw": amount, "final": final,
                "attacker": attacker,
            })
            return actual

        # 4. 普通受击（走护甲 + 套装百分比减伤）
        final, actual = p.stats.take_damage_with_defense(amount, element=element)
        if actual > 0:
            p.hurt_timer = self.hurt_stagger
            if knockback_dir != 0:
                self.kb.apply(knockback_dir, HURT_KNOCKBACK_FORCE)

        # 5. 状态切换
        if p.stats.is_dead:
            # 死亡由 GameScene 的 update 循环统一处理（显示死亡界面等）
            # 此处不切换状态，仅发射事件
            event_manager.emit("player_death", {"x": p.x, "y": p.y})
        elif actual > 0:
            p.fsm.change_state("Hurt")
            event_manager.emit("player_hurt", {
                "damage": actual, "raw": amount, "final": final,
                "attacker": attacker,
            })

        return actual

    # ----------------------------------------------------------------
    # 接口便捷：弹反 / 格挡查询
    # ----------------------------------------------------------------

    def is_blocking(self) -> bool:
        return self.block.is_blocking

    def in_parry_window(self) -> bool:
        return self.block.parry_window.is_open

    # ----------------------------------------------------------------
    # 击退速度（每帧由 Player.update 调用）
    # ----------------------------------------------------------------

    def consume_knockback(self, dt: float) -> float:
        return self.kb.consume(dt)
