# =============================================================
# entities/player/player_states.py —— 玩家状态机各状态
#
# 第 4 阶段重构：
#   - 攻击连段使用 combat.combo_system.ComboWindow 统一管理
#   - 新增 BlockState（按 L 键进入格挡）
# =============================================================
from __future__ import annotations
from typing import TYPE_CHECKING
from utils.state_machine import State
from combat.combo_system import ComboWindow, ComboChain, DEFAULT_LIGHT_CHAIN

if TYPE_CHECKING:
    from entities.player.player import Player


# ---- 辅助基类 ----

class PlayerState(State):
    """所有玩家状态的基类，持有 player 引用"""

    def __init__(self, name: str):
        super().__init__(name)

    @property
    def player(self) -> "Player":
        return self.machine.owner   # type: ignore


# =============================================================
# Idle —— 站立待机
# =============================================================

class IdleState(PlayerState):
    def __init__(self):
        super().__init__("Idle")

    def on_enter(self, prev_state=None):
        self.player.vel_x = 0.0

    def update(self, dt: float):
        p = self.player
        inp = p.inp

        # 受伤检测
        if p.hurt_timer > 0:
            self.machine.change_state("Hurt")
            return

        # 移动
        if inp.axis_x != 0:
            self.machine.change_state("Run")
            return

        # 跳跃
        if p.jump_requested:
            p.jump_requested = False
            self.machine.change_state("Jump")
            return

        # 翻滚
        if p.roll_requested:
            p.roll_requested = False
            self.machine.change_state("Roll")
            return

        # 格挡（按住 L 键进入）
        if p.inp.is_pressed("block"):
            self.machine.change_state("Block")
            return

        # 轻攻击
        if p.light_attack_requested:
            p.light_attack_requested = False
            self.machine.change_state("LightAttack1")
            return

        # 重攻击
        if p.heavy_attack_requested:
            p.heavy_attack_requested = False
            self.machine.change_state("HeavyAttack")
            return

        # 离地则切换为下落
        if not p.gravity.on_ground:
            self.machine.change_state("Fall")


# =============================================================
# Run —— 跑步
# =============================================================

class RunState(PlayerState):
    def __init__(self):
        super().__init__("Run")

    def update(self, dt: float):
        p = self.player
        inp = p.inp

        if p.hurt_timer > 0:
            self.machine.change_state("Hurt")
            return

        axis = inp.axis_x
        if axis == 0:
            self.machine.change_state("Idle")
            return

        if p.jump_requested:
            p.jump_requested = False
            self.machine.change_state("Jump")
            return

        if p.roll_requested:
            p.roll_requested = False
            self.machine.change_state("Roll")
            return

        # 格挡（按住 L 键）
        if p.inp.is_pressed("block"):
            self.machine.change_state("Block")
            return

        if p.light_attack_requested:
            p.light_attack_requested = False
            self.machine.change_state("LightAttack1")
            return

        if not p.gravity.on_ground:
            self.machine.change_state("Fall")


# =============================================================
# Jump —— 跳跃（上升阶段）
# =============================================================

class JumpState(PlayerState):
    def __init__(self):
        super().__init__("Jump")

    def on_enter(self, prev_state=None):
        p = self.player
        # 实际跳跃力
        if p.gravity.can_jump or p.coyote_timer > 0:
            p.gravity.jump()
            p.coyote_timer = 0.0

    def update(self, dt: float):
        p = self.player
        if p.hurt_timer > 0:
            self.machine.change_state("Hurt")
            return

        # 空中轻攻击
        if p.light_attack_requested:
            p.light_attack_requested = False
            self.machine.change_state("LightAttack1")
            return

        # 空中重攻击
        if p.heavy_attack_requested:
            p.heavy_attack_requested = False
            self.machine.change_state("HeavyAttack")
            return

        # 速度由正转负（开始下落）
        if p.gravity.vel_y >= 0:
            self.machine.change_state("Fall")
            return
        # 落地
        if p.gravity.on_ground:
            self.machine.change_state("Idle")


# =============================================================
# Fall —— 下落
# =============================================================

class FallState(PlayerState):
    def __init__(self):
        super().__init__("Fall")

    def update(self, dt: float):
        p = self.player
        if p.hurt_timer > 0:
            self.machine.change_state("Hurt")
            return

        # 空中轻攻击
        if p.light_attack_requested:
            p.light_attack_requested = False
            self.machine.change_state("LightAttack1")
            return

        # 空中重攻击
        if p.heavy_attack_requested:
            p.heavy_attack_requested = False
            self.machine.change_state("HeavyAttack")
            return

        if p.gravity.on_ground:
            self.machine.change_state("Idle")


# =============================================================
# Roll —— 翻滚（闪避）
# =============================================================

ROLL_SPEED       = 400.0    # 翻滚速度 px/s
ROLL_DURATION    = 0.35     # 翻滚持续时间 s
ROLL_INVINCIBLE_START = 0.05  # 无敌帧开始（s 后）
ROLL_INVINCIBLE_END   = 0.28  # 无敌帧结束（s 后）
ROLL_STAMINA_COST     = 25.0


class RollState(PlayerState):
    def __init__(self):
        super().__init__("Roll")
        self._timer  = 0.0
        self._dir    = 1
        self._speed  = 400.0   # 运行时从 growth_stats 覆盖
        self._inv_start = ROLL_INVINCIBLE_START
        self._inv_end   = ROLL_INVINCIBLE_END

    def on_enter(self, prev_state=None):
        p = self.player

        # 读取成长属性决定的翻滚参数
        growth = getattr(p, "growth", None)
        if growth is not None:
            from entities.player.growth_stats import RollType
            params = growth.roll_params
            # 无法翻滚：负重 > 100%
            if growth.roll_type == RollType.UNABLE:
                self.machine.change_state("Idle")
                return
            self._speed     = params["speed"]
            roll_dur        = params["duration"]
            self._inv_start = params["inv_start"]
            self._inv_end   = params["inv_end"]
        else:
            roll_dur = ROLL_DURATION

        if not p.stats.consume_stamina(ROLL_STAMINA_COST):
            self.machine.change_state("Idle")
            return

        self._timer      = roll_dur
        self._total_dur  = roll_dur
        inp_x            = p.inp.axis_x
        self._dir        = inp_x if inp_x != 0 else p.facing
        p.facing         = self._dir
        p.invincible     = False

    def on_exit(self, next_state=None):
        self.player.invincible = False

    def update(self, dt: float):
        p = self.player
        self._timer -= dt

        total = getattr(self, "_total_dur", ROLL_DURATION)
        elapsed = total - self._timer
        p.invincible = (self._inv_start <= elapsed <= self._inv_end)

        p.vel_x = self._dir * self._speed

        if self._timer <= 0:
            p.vel_x = 0.0
            self.machine.change_state("Idle")


# =============================================================
# LightAttack1/2/3 —— 轻攻击三连段
# =============================================================

# (伤害, 耐力消耗, 判定框宽, 判定框高, offset_x, offset_y, 前摇帧, 判定帧, 后摇帧)
_LIGHT_COMBO = [
    dict(damage=18, stamina=15.0, w=40, h=36, ox=28, oy=-8,  pre=3, active=4, post=8),
    dict(damage=22, stamina=15.0, w=44, h=40, ox=30, oy=-10, pre=3, active=5, post=8),
    dict(damage=30, stamina=20.0, w=50, h=44, ox=32, oy=-6,  pre=4, active=6, post=10),
]

HEAVY_ATTACK_DATA = dict(
    damage=55, stamina=30.0, w=56, h=52, ox=32, oy=-8, pre=8, active=6, post=14
)


class _AttackBaseState(PlayerState):
    """轻/重攻击状态基类，处理帧计数和判定框生成（使用 ComboWindow）。"""

    def __init__(self, name: str, data: dict, next_state: str = "Idle",
                 combo_state: str = "", combo_step: int = 0,
                 is_heavy: bool = False):
        super().__init__(name)
        self._data_fallback  = data          # 无武器时的兜底数值
        self._next           = next_state
        self._combo          = combo_state    # 兼容字段（链尾时为 ""）
        self._combo_step     = combo_step    # 0/1/2 → 传给 weapon.get_light_attack()
        self._is_heavy       = is_heavy
        self._frame          = 0
        self._total          = data["pre"] + data["active"] + data["post"]
        # ComboWindow 组件
        self._combo_window: ComboWindow = ComboWindow()

    def _get_data(self) -> dict:
        """
        从玩家当前武器读取攻击数据（AttackData），
        转换为兼容旧格式的 dict。无武器时使用 _data_fallback。
        """
        p = self.player
        weapon = getattr(p, "weapon", None)
        if weapon is None:
            return self._data_fallback

        if self._is_heavy:
            wd = weapon.get_heavy_attack()
        else:
            wd = weapon.get_light_attack(self._combo_step)

        # 时序从兜底数据中继承（武器只覆盖伤害/范围/元素）
        fb = self._data_fallback
        data = {
            "damage":  wd.damage,
            "stamina": wd.stamina_cost,
            "w":       wd.hb_width,
            "h":       wd.hb_height,
            "ox":      wd.hb_offset_x,
            "oy":      wd.hb_offset_y,
            "pre":     fb["pre"],
            "active":  wd.active_frames,
            "post":    fb["post"],
            # 武器额外字段
            "element":      wd.element,
            "poise_damage": wd.poise_damage,
            "knockback":    wd.knockback,
            "bleed_stack":  wd.bleed_stack,
            "poison_stack": wd.poison_stack,
        }

        # ---- 第 12 阶段修复：武器附魔 Buff 覆盖元素 ----
        if p is not None:
            stats = getattr(p, "stats", None)
            if stats is not None:
                override = stats.get_weapon_element_override()
                if override:
                    data["element"] = override

        return data

    @staticmethod
    def _should_fire_projectile(weapon, is_heavy: bool = False) -> bool:
        """判断武器是否为远程（攻击时生成抛射物而非近战 hitbox）。
        弓：轻/重攻击均发射；法杖：仅重攻击发射魔法弹，轻攻击为近战拍击。
        """
        from weapons.base_weapon import WeaponType
        wt = getattr(weapon, "weapon_type", "")
        if wt == WeaponType.BOW:
            return True
        if wt == WeaponType.STAFF:
            return is_heavy
        return False

    def _fire_projectile(self, weapon, p: "Player", data: dict) -> None:
        """发射远程抛射物（弓/法杖）——复用与敌人弓箭手 AI 完全相同的逻辑。"""
        import logging
        _log = logging.getLogger(__name__)
        from weapons.base_weapon import WeaponType
        from physics.projectile import Arrow, MagicBall

        wt = getattr(weapon, "weapon_type", "")

        area = getattr(p, "current_area", None)
        if area is None or not hasattr(area, "projectiles"):
            _log.warning("_fire_projectile: area 无效")
            return

        facing = p.facing or 1

        if wt == WeaponType.BOW:
            # 与 archer._fire_arrow 完全一致的发射逻辑
            from weapons.types.bow import _consume_arrow
            if not _consume_arrow(p):
                return
            wd = weapon.get_light_attack(0) if not self._is_heavy else weapon.get_heavy_attack()
            # 武器附魔 Buff 覆盖元素
            arrow_element = wd.element
            ov = p.stats.get_weapon_element_override()
            if ov:
                arrow_element = ov
            spawn_x = p.rect.centerx + facing * 14
            spawn_y = p.rect.centery - 4
            arrow = Arrow(
                x=spawn_x, y=spawn_y,
                vx=700.0 * facing if not self._is_heavy else 820.0 * facing,
                vy=-40.0,
                damage=wd.damage,
                owner=p,
                element=arrow_element,
                poise_damage=wd.poise_damage,
                lifetime=2.0,
            )
            area.projectiles.append(arrow)
            _log.debug("_fire_projectile BOW: arrow at (%d,%d) vx=%d dmg=%d → projectiles=%d",
                       int(spawn_x), int(spawn_y), int(arrow.vx), arrow.damage,
                       len(area.projectiles))

        elif wt == WeaponType.STAFF:
            # 法杖重攻击：消耗灵力发射魔法弹
            HEAVY_MANA_COST = getattr(weapon, "HEAVY_MANA_COST", 8)
            if not p.stats.consume_mana(HEAVY_MANA_COST):
                _log.debug("_fire_projectile STAFF: mana 不足 (need=%d, have=%d)",
                          HEAVY_MANA_COST, p.stats.mana)
                return
            wd = weapon.get_heavy_attack()
            # 武器附魔 Buff 覆盖元素
            ball_element = wd.element
            ov = p.stats.get_weapon_element_override()
            if ov:
                ball_element = ov
            ball = MagicBall(
                x=p.rect.centerx + facing * 18,
                y=p.rect.centery - 4,
                vx=560.0 * facing,
                vy=0.0,
                damage=wd.damage,
                owner=p,
                element=ball_element,
                poise_damage=wd.poise_damage,
                lifetime=2.5,
            )
            area.projectiles.append(ball)
            _log.debug("_fire_projectile STAFF: ball at (%d,%d) vx=%d",
                       int(ball.x), int(ball.y), int(ball.vx))

    def on_enter(self, prev_state=None):
        p = self.player
        data = self._get_data()
        self._total = data["pre"] + data["active"] + data["post"]
        if not p.stats.consume_stamina(data["stamina"]):
            self.machine.change_state("Idle")
            return
        self._frame           = 0
        p.vel_x               = 0.0

        # ---- 远程武器：在 on_enter 时生成抛射物，不再创建 hitbox ----
        weapon = getattr(p, "weapon", None)
        if weapon is not None and self._should_fire_projectile(weapon, self._is_heavy):
            self._fire_projectile(weapon, p, data)
            # 标记本轮攻击已发射，update 中不再生成 hitbox
            self._projectile_fired = True
        else:
            self._projectile_fired = False

        # 初始化 ComboWindow：连段输入窗口在「判定帧开始时」打开
        if self._combo:
            chain = ComboChain([self.name, self._combo])
            self._combo_window.reset(chain, self.name,
                                     window_open_frame=data["pre"])

    def update(self, dt: float):
        p = self.player
        data = self._get_data()
        self._frame += 1
        self._combo_window.tick()

        # 在判定帧内生成攻击框（远程武器已发射抛射物则跳过）
        if data["pre"] <= self._frame < data["pre"] + data["active"]:
            if self._frame == data["pre"] and not self._projectile_fired:
                from entities.player.attack_hitbox import AttackHitbox
                hb = AttackHitbox(
                    owner_rect    = p.rect,
                    facing        = p.facing,
                    offset_x      = data["ox"],
                    offset_y      = data["oy"],
                    width         = data["w"],
                    height        = data["h"],
                    damage        = data["damage"],
                    active_frames = data["active"],
                    knockback     = data.get("knockback", 180.0),
                    element       = data.get("element", "none"),
                    poise_damage  = data.get("poise_damage", 10.0),
                    bleed_stack   = data.get("bleed_stack", 0.0),
                    poison_stack  = data.get("poison_stack", 0.0),
                    source        = p,
                )
                p.active_hitboxes.append(hb)

        # 收集连段输入（整个攻击过程中持续监听，由 ComboWindow 决定窗口）
        if self._combo and p.light_attack_requested:
            self._combo_window.push_input(True)
            p.light_attack_requested = False

        # 状态结束
        if self._frame >= self._total:
            next_combo = self._combo_window.consume_next() if self._combo else None
            if next_combo:
                self.machine.change_state(next_combo)
            else:
                if not p.gravity.on_ground:
                    self.machine.change_state("Fall")
                else:
                    self.machine.change_state(self._next)


class LightAttack1State(_AttackBaseState):
    def __init__(self):
        super().__init__("LightAttack1", _LIGHT_COMBO[0],
                         next_state="Idle", combo_state="LightAttack2",
                         combo_step=0, is_heavy=False)


class LightAttack2State(_AttackBaseState):
    def __init__(self):
        super().__init__("LightAttack2", _LIGHT_COMBO[1],
                         next_state="Idle", combo_state="LightAttack3",
                         combo_step=1, is_heavy=False)


class LightAttack3State(_AttackBaseState):
    def __init__(self):
        super().__init__("LightAttack3", _LIGHT_COMBO[2],
                         next_state="Idle", combo_state="",
                         combo_step=2, is_heavy=False)


class HeavyAttackState(_AttackBaseState):
    def __init__(self):
        super().__init__("HeavyAttack", HEAVY_ATTACK_DATA,
                         next_state="Idle", combo_state="",
                         combo_step=0, is_heavy=True)


# =============================================================
# Hurt —— 受击硬直
# =============================================================

HURT_DURATION = 0.30   # 硬直时间 s


class HurtState(PlayerState):
    def __init__(self):
        super().__init__("Hurt")
        self._timer = 0.0

    def on_enter(self, prev_state=None):
        self._timer = HURT_DURATION
        self.player.vel_x = 0.0

    def update(self, dt: float):
        self._timer -= dt
        if self._timer <= 0:
            if self.player.stats.is_dead:
                self.machine.change_state("Dead")
            else:
                self.machine.change_state("Idle")


# =============================================================
# Dead —— 死亡
# =============================================================

class DeadState(PlayerState):
    def __init__(self):
        super().__init__("Dead")
        self._timer = 0.0

    def on_enter(self, prev_state=None):
        self._timer  = 2.0   # 2 秒后触发死亡逻辑
        p = self.player
        p.vel_x = 0.0
        p.active_hitboxes.clear()

    def update(self, dt: float):
        self._timer -= dt
        if self._timer <= 0:
            from core.event_manager import event_manager
            event_manager.emit("player_dead", {})
            self._timer = 999   # 防止重复触发


# =============================================================
# Block —— 格挡（按住 L 键）
# =============================================================

class BlockState(PlayerState):
    """
    持续按住格挡键时停留的状态：
      - 移动锁定（vel_x = 0）
      - 自动同步 BlockComponent.is_blocking（由 PlayerCombat.update 处理）
      - 释放格挡键时回到 Idle
      - 受击时若处于弹反窗口由 PlayerCombat 自动转为弹反
    """

    def __init__(self):
        super().__init__("Block")

    def on_enter(self, prev_state=None):
        self.player.vel_x = 0.0

    def update(self, dt: float):
        p = self.player
        # 受击优先
        if p.hurt_timer > 0:
            self.machine.change_state("Hurt")
            return

        # 释放格挡键
        if not p.inp.is_pressed("block"):
            self.machine.change_state("Idle")
            return

        # 翻滚优先级高于格挡
        if p.roll_requested:
            p.roll_requested = False
            self.machine.change_state("Roll")
            return

        # 落地状态保持
        if not p.gravity.on_ground:
            self.machine.change_state("Fall")
            return

        # 在 Block 状态下吃掉攻击请求（不允许同时格挡+攻击）
        p.light_attack_requested = False
        p.heavy_attack_requested = False
        p.vel_x = 0.0
