# =============================================================
# entities/enemy/enemy_ai.py —— 敌人 AI 状态机（5 态完整闭环）
# =============================================================
#
# 状态闭环（按 game_rule.md §4.2）：
#   [Idle/Patrol] -- 视野内 + 累积警觉值 -->  [Alert]
#                   <-- 失去视野/超时 --
#
#   [Alert]    -- 警觉值满 -->                [Chase]
#              -- 失去视野/距离过远 -->       [Return]
#
#   [Chase]    -- 进入攻击范围 -->            [Attack]
#              -- 离开追击半径 -->            [Return]
#
#   [Attack]   -- 攻击结束 + 仍可见 -->       [Chase]
#              -- 攻击结束 + 不可见 -->       [Alert]
#
#   [Return]   -- 回到出生点附近 -->          [Idle]
#              -- 玩家再次进入视野 -->        [Alert]
#
#   [Hurt]     -- 短暂硬直 --> Chase / Alert
#   [Dead]     -- 倒地 0.8s --> 派 enemy_dead 事件
#
# 注：旧文件 entities/enemy/enemy_states.py 仍可作为兼容层
#     re-export 本模块的 5 个核心状态以保留旧 import 路径。
# =============================================================
from __future__ import annotations

from utils.state_machine import State
from core.event_manager  import event_manager


# ---- 时间常量 ----
HURT_DURATION  = 0.4   # 受击硬直（秒）
DEAD_DURATION  = 0.8   # 死亡倒地（秒）

# 攻击阶段帧数（60 fps）
ATK_WINDUP_F   = 8
ATK_ACTIVE_F   = 6
ATK_COOLDOWN_F = 10

# 攻击阶段枚举（供 base_enemy 渲染读取）
ATK_PHASE_WINDUP   = "windup"
ATK_PHASE_ACTIVE   = "active"
ATK_PHASE_COOLDOWN = "cooldown"
ATK_PHASE_NONE     = "none"

# ---- 警戒（Alert）参数默认值 ----
DEFAULT_ALERT_THRESHOLD = 0.5     # 警觉值满阈值
DEFAULT_ALERT_SPEED     = 1.5     # 视野内警觉值累积速度（/秒）
DEFAULT_ALERT_DECAY     = 0.5     # 视野丢失后衰减速度（/秒）
ALERT_TURN_TIME         = 0.3     # 警戒时转向 + 短暂停顿（秒）

# ---- 回归（Return）参数 ----
RETURN_HOME_TOLERANCE   = 8.0     # 距离出生点多近算"已回家"
RETURN_HEAL_PER_SEC     = 8       # Return 状态每秒回血量

# ---- 跳跃越障 ----
JUMP_PROBE_W      = 4
JUMP_PROBE_H      = 20
JUMP_COOLDOWN     = 1.2


# =============================================================
# Idle / Patrol 状态
# =============================================================

class EnemyIdleState(State):
    """待机并在出生点附近左右巡逻。检测玩家进入视野后转 Alert。"""

    def __init__(self):
        super().__init__("Idle")
        self._wait_timer: float = 0.0

    def on_enter(self, prev_state=None):
        e = self.machine.owner
        self._wait_timer = 0.5
        e.vel_x = 0.0

    def update(self, dt: float):
        e = self.machine.owner

        # 视野内即进入 Alert（不再直接 Chase，体现警戒过渡）
        target = e._get_ai_target()
        if target and e._distance_to_target(target) <= e.stats.sight_range:
            self.machine.change_state("Alert")
            return

        # 巡逻中也缓慢衰减警觉值
        e.alert_value = max(0.0, e.alert_value - e.stats.alert_decay * dt)

        if self._wait_timer > 0:
            self._wait_timer -= dt
            e.vel_x = 0.0
            return

        radius  = e.stats.patrol_radius
        left_x  = e.spawn_x - radius
        right_x = e.spawn_x + radius

        if e.facing == 0:
            e.facing = 1

        target_x = right_x if e.facing > 0 else left_x
        dist     = abs(e.x - target_x)

        if dist < 4.0:
            e.facing         = -e.facing
            e.vel_x          = 0.0
            self._wait_timer = 0.6
        else:
            e.vel_x = e.facing * e.stats.speed

        if e.gravity.on_ground and abs(e.vel_x) > 5.0:
            _try_jump_over_obstacle(e, dt)


# =============================================================
# Alert 状态（警戒）
# =============================================================

class EnemyAlertState(State):
    """
    发现玩家但尚未确认目标。
    - 转向玩家 + 站定（短暂停顿，给玩家"被发现"反馈）
    - 警觉值快速累积，满阈值后进入 Chase
    - 视野丢失则回到 Idle（警觉值会缓慢衰减）
    """

    def __init__(self):
        super().__init__("Alert")
        self._turn_timer: float = 0.0

    def on_enter(self, prev_state=None):
        e = self.machine.owner
        e.vel_x = 0.0
        self._turn_timer = ALERT_TURN_TIME
        # 朝向目标
        target = e._get_ai_target()
        if target:
            e.facing = 1 if target.x > e.x else -1
        # 派事件给特效层（可加感叹号 "！" 提示符）
        event_manager.emit("enemy_alerted", {"enemy": e})

    def update(self, dt: float):
        e = self.machine.owner

        if self._turn_timer > 0:
            self._turn_timer -= dt
            e.vel_x = 0.0

        target = e._get_ai_target()
        # 目标在视野内 → 累积警觉值
        if target and e._distance_to_target(target) <= e.stats.sight_range:
            e.facing = 1 if target.x > e.x else -1
            e.alert_value = min(1.0, e.alert_value + e.stats.alert_speed * dt)

            # 警觉值满 → 转 Chase
            if e.alert_value >= e.stats.alert_threshold:
                self.machine.change_state("Chase")
                return
        else:
            # 视野丢失 → 衰减；归零后回 Idle
            e.alert_value = max(0.0, e.alert_value - e.stats.alert_decay * dt)
            if e.alert_value <= 0.0:
                self.machine.change_state("Idle")
                return


# =============================================================
# Chase 状态
# =============================================================

class EnemyChaseState(State):
    """追击玩家，遇到障碍自动起跳。"""

    def __init__(self):
        super().__init__("Chase")

    def on_enter(self, prev_state=None):
        # 进入战斗状态时警觉值锁满，方便 Hurt → Chase 平滑回归
        e = self.machine.owner
        e.alert_value = 1.0

    def update(self, dt: float):
        e = self.machine.owner

        target = e._get_ai_target()
        # 目标死亡或超出追击范围 → Return
        if not target or getattr(target, "is_dead", False):
            self.machine.change_state("Return")
            return

        dist_to_target = e._distance_to_target(target)
        if dist_to_target > e.stats.lose_range:
            self.machine.change_state("Return")
            return

        dx   = target.x - e.x
        dist = abs(dx)

        # 弓箭手 / 法师子类可重写 try_ranged_attack 提前发动远程
        if hasattr(e, "try_ranged_attack") and e.try_ranged_attack(dist):
            return

        # 进入近战范围 → Attack
        if dist <= e.stats.attack_range:
            self.machine.change_state("Attack")
            return

        e.facing = 1 if dx > 0 else -1
        e.vel_x  = e.facing * e.stats.speed

        if e.gravity.on_ground and abs(e.vel_x) > 5.0:
            _try_jump_over_obstacle(e, dt)


# =============================================================
# Attack 状态（近战）
# =============================================================

class EnemyAttackState(State):
    """三段时序：前摇（白框警告）→ 判定（橙黄）→ 后摇（消退）"""

    _TOTAL_FRAMES = ATK_WINDUP_F + ATK_ACTIVE_F + ATK_COOLDOWN_F

    def __init__(self):
        super().__init__("Attack")
        self._frame: int     = 0
        self._hit_done: bool = False

    def on_enter(self, prev_state=None):
        self._frame    = 0
        self._hit_done = False
        self.machine.owner.vel_x = 0.0

    @property
    def atk_phase(self) -> str:
        if self._frame < ATK_WINDUP_F:
            return ATK_PHASE_WINDUP
        if self._frame < ATK_WINDUP_F + ATK_ACTIVE_F:
            return ATK_PHASE_ACTIVE
        return ATK_PHASE_COOLDOWN

    def update(self, dt: float):
        e = self.machine.owner
        self._frame += 1

        target = e._get_ai_target()
        # 判定窗口
        if ATK_WINDUP_F <= self._frame < ATK_WINDUP_F + ATK_ACTIVE_F:
            if not self._hit_done and target:
                atk_rect = e._get_attack_rect()
                if atk_rect.colliderect(target.rect):
                    knockback_dir = 1 if target.x > e.x else -1
                    try:
                        target.take_damage(e.stats.atk, knockback_dir,
                                           attacker=e)
                    except TypeError:
                        target.take_damage(e.stats.atk, knockback_dir)
                    self._hit_done = True

        if self._frame >= self._TOTAL_FRAMES:
            if target and e._distance_to_target(target) <= e.stats.sight_range:
                self.machine.change_state("Chase")
            else:
                self.machine.change_state("Alert")


# =============================================================
# Return 状态（回归）
# =============================================================

class EnemyReturnState(State):
    """
    回归出生点：
    - 走回 spawn_x（纵向位置不强制）
    - 缓慢回血（per second 8 HP）
    - 到家后清空警觉值并切回 Idle
    - 回归途中再次发现玩家可立即转入 Alert
    """

    def __init__(self):
        super().__init__("Return")

    def on_enter(self, prev_state=None):
        pass

    def update(self, dt: float):
        e = self.machine.owner

        # 中途又发现目标
        target = e._get_ai_target()
        if target and e._distance_to_target(target) <= e.stats.sight_range:
            self.machine.change_state("Alert")
            return

        # 回血
        if e.stats.hp < e.stats.max_hp and RETURN_HEAL_PER_SEC > 0:
            heal_amount = RETURN_HEAL_PER_SEC * dt
            # 累积小数到 _return_heal_acc
            acc = getattr(e, "_return_heal_acc", 0.0) + heal_amount
            int_part = int(acc)
            if int_part > 0:
                e.stats.heal(int_part)
                acc -= int_part
            e._return_heal_acc = acc

        # 回家
        dx = e.spawn_x - e.x
        if abs(dx) <= RETURN_HOME_TOLERANCE:
            e.vel_x = 0.0
            e.alert_value = 0.0
            self.machine.change_state("Idle")
            return

        e.facing = 1 if dx > 0 else -1
        e.vel_x  = e.facing * e.stats.speed * 0.85   # 回归速度略慢

        if e.gravity.on_ground and abs(e.vel_x) > 5.0:
            _try_jump_over_obstacle(e, dt)


# =============================================================
# Hurt 状态
# =============================================================

class EnemyHurtState(State):
    """受击硬直 HURT_DURATION 秒。"""

    def __init__(self):
        super().__init__("Hurt")
        self._timer: float = 0.0

    def on_enter(self, prev_state=None):
        self._timer = HURT_DURATION
        self.machine.owner.vel_x = 0.0

    def update(self, dt: float):
        self._timer -= dt
        if self._timer <= 0:
            e = self.machine.owner
            target = e._get_ai_target()
            if target and e._distance_to_target(target) <= e.stats.sight_range:
                # 受击后直接进入 Chase（已确认目标）
                self.machine.change_state("Chase")
            else:
                self.machine.change_state("Alert")


# =============================================================
# Dead 状态
# =============================================================

class EnemyDeadState(State):
    """死亡倒地 DEAD_DURATION 秒后发布事件并销毁。"""

    def __init__(self):
        super().__init__("Dead")
        self._timer: float  = 0.0
        self._emitted: bool = False

    def on_enter(self, prev_state=None):
        self._timer   = DEAD_DURATION
        self._emitted = False
        self.machine.owner.vel_x = 0.0

    def update(self, dt: float):
        if self._emitted:
            return
        self._timer -= dt
        if self._timer <= 0:
            e = self.machine.owner
            e.dead   = True
            e.active = False
            self._emitted = True
            event_manager.emit("enemy_dead", {"enemy": e})


# =============================================================
# 跳跃越障辅助函数
# =============================================================

def _try_jump_over_obstacle(e, dt: float):
    """
    检测敌人正前方是否有低矮障碍，若有则触发跳跃。
    详见 enemy_states.py 中相同函数的注释。
    """
    if getattr(e, "_jump_cooldown", 0.0) > 0:
        return

    if abs(e.vel_x) < 5.0:
        return
    moving_forward = (e.facing > 0 and e.vel_x > 0) or (e.facing < 0 and e.vel_x < 0)
    if not moving_forward:
        return

    cmap = getattr(e, "_last_collision_map", None)
    if cmap is None:
        return

    import pygame
    r = e.rect

    gap = 2
    if e.facing > 0:
        probe_x = r.right + gap
    else:
        probe_x = r.left - JUMP_PROBE_W - gap

    low_probe  = pygame.Rect(probe_x, r.centery + 4, JUMP_PROBE_W, r.height // 2 - 4)
    high_probe = pygame.Rect(probe_x, r.top, JUMP_PROBE_W, r.height // 2)

    has_low_wall  = bool(cmap.get_solid_tiles_in_rect(low_probe))
    has_high_wall = bool(cmap.get_solid_tiles_in_rect(high_probe))

    if has_low_wall and not has_high_wall:
        e.gravity.jump()
        e._jump_cooldown = JUMP_COOLDOWN


# =============================================================
# 注册辅助：给 BaseEnemy 一次性挂上完整状态集
# =============================================================

def register_default_states(fsm) -> None:
    """
    给敌人状态机一次性添加 7 个标准状态：
        Idle / Alert / Chase / Attack / Return / Hurt / Dead
    """
    fsm.add_states(
        EnemyIdleState(),
        EnemyAlertState(),
        EnemyChaseState(),
        EnemyAttackState(),
        EnemyReturnState(),
        EnemyHurtState(),
        EnemyDeadState(),
    )


__all__ = [
    "EnemyIdleState", "EnemyAlertState", "EnemyChaseState",
    "EnemyAttackState", "EnemyReturnState", "EnemyHurtState",
    "EnemyDeadState",
    "ATK_WINDUP_F", "ATK_ACTIVE_F", "ATK_COOLDOWN_F",
    "ATK_PHASE_WINDUP", "ATK_PHASE_ACTIVE", "ATK_PHASE_COOLDOWN",
    "ATK_PHASE_NONE",
    "register_default_states",
]
