# =============================================================
# entities/enemy/base_enemy.py —— 敌人基类
# =============================================================
from __future__ import annotations

import pygame
from typing import Optional, TYPE_CHECKING

from entities.base_entity        import BaseEntity
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.enemy_ai     import (
    register_default_states,
    ATK_WINDUP_F, ATK_ACTIVE_F,
    ATK_PHASE_WINDUP, ATK_PHASE_ACTIVE, ATK_PHASE_COOLDOWN,
)
from physics.gravity             import GravitySystem
from physics.movement_resolver   import MovementResolver
from utils.state_machine         import StateMachine
from utils.color                 import WHITE
from combat.status_manager       import StatusManager
from combat.knockback            import KnockbackComponent
from combat.drop_system          import DropEntry
import utils.debug as debug

if TYPE_CHECKING:
    from map.collision_map      import CollisionMap
    from entities.player.player import Player


# ---- 敌人默认尺寸 ----
ENEMY_W = 24
ENEMY_H = 48

# ---- HP 血条 ----
BAR_W  = 36
BAR_H  = 4
BAR_OY = 10   # 血条底部距实体顶部的像素数（向上偏移）

# ---- 韧性条（在血条下方）----
POISE_BAR_H   = 3                    # 韧性条高度
POISE_BAR_GAP = 2                    # 与血条的垂直间距（向下）
POISE_CLR_BG  = (45, 45, 45)        # 背景（深灰）
POISE_CLR_FG  = (200, 200, 210)     # 前景（灰白）
POISE_CLR_LOW = (120, 120, 140)     # 韧性偏低时（< 30%）变暗

# ---- 攻击框几何 ----
ATK_BOX_REACH  = 36    # 碰撞箱边缘向前延伸距离(px)
ATK_BOX_HEIGHT = 32    # 攻击框高度(px)

# ---- 攻击框三段颜色（RGBA） ----
#   前摇：白色半透明 —— 给玩家警告信号，此时不造成伤害
#   判定：橙黄亮色   —— 伤害窗口激活
#   后摇：淡橙渐隐   —— 动作收招
_CLR_WINDUP_FILL   = (255, 255, 255, 80)    # 白色，低透明度
_CLR_WINDUP_BORDER = (255, 255, 255, 220)   # 白色边框

_CLR_ACTIVE_FILL   = (255, 180,  30, 160)   # 橙黄，高透明度
_CLR_ACTIVE_BORDER = (255, 230,  50)        # 亮黄边框

_CLR_COOLDOWN_FILL  = (200,  80,  20,  40)  # 暗橙，几乎透明
_CLR_COOLDOWN_BORDER= (160,  70,  20)       # 暗橙边框

# ---- 打击白闪 ----
_HIT_FLASH_DURATION = 0.12


class BaseEnemy(BaseEntity):
    """所有敌人基类。子类重写 _build_stats() 和 color。"""

    color: tuple = (120, 200, 80)

    # 子类覆盖此属性来定义掉落表，格式：List[DropEntry]
    drop_table: list = []

    def __init__(self, x: float, y: float,
                 width: int = ENEMY_W, height: int = ENEMY_H):
        super().__init__(x, y, width, height)

        self.spawn_x: float = x
        self.spawn_y: float = y

        self.stats: EnemyStats = self._build_stats()

        self.gravity  = GravitySystem()
        self.resolver = MovementResolver()

        self.player: Optional["Player"] = None

        # 击退组件（替换原来的 _knockback_vx 字段）
        self.kb: KnockbackComponent = KnockbackComponent()
        # 兼容字段：旧代码可能仍读 _knockback_vx
        self._knockback_vx:       float = 0.0
        self._hit_flash:          float = 0.0
        self._jump_cooldown:      float = 0.0
        # 保存最后一次 collision_map，供跳跃探针使用
        self._last_collision_map: Optional["CollisionMap"] = None

        # 冰冻 / 眩晕标记（由 StatusEffect 写入）
        self.frozen:  bool = False
        self.stunned: bool = False

        # 状态异常管理器（FloatingTextManager 在 game_scene 里 bind）
        self.status: StatusManager = StatusManager(owner=self)

        # 警觉值（0.0 ~ 1.0），由 EnemyAlertState 累积/衰减
        self.alert_value: float = 0.0
        # 回归状态回血累加器（避免每帧浮点丢失）
        self._return_heal_acc: float = 0.0

        # 状态机（注册 7 个标准状态：Idle/Alert/Chase/Attack/Return/Hurt/Dead）
        self.fsm = StateMachine(owner=self)
        register_default_states(self.fsm)
        self.fsm.change_state("Idle")

    # ----------------------------------------------------------------
    # 子类接口
    # ----------------------------------------------------------------

    def _build_stats(self) -> EnemyStats:
        return EnemyStats()

    # ----------------------------------------------------------------
    # 攻击框（碰撞检测 + 渲染共用）
    # ----------------------------------------------------------------

    def _get_attack_rect(self) -> pygame.Rect:
        """返回攻击判定矩形（世界坐标），朝向前方。"""
        r = self.rect
        w = self._hb_w + ATK_BOX_REACH
        h = ATK_BOX_HEIGHT
        if self.facing >= 0:
            ax = r.centerx
        else:
            ax = r.centerx - w
        ay = r.centery - h // 2
        return pygame.Rect(ax, ay, w, h)

    # ----------------------------------------------------------------
    # 感知辅助
    # ----------------------------------------------------------------

    def _distance_to_player(self) -> float:
        if self.player is None:
            return float("inf")
        import math
        return math.sqrt((self.x - self.player.x) ** 2 +
                         (self.y - self.player.y) ** 2)

    def _can_see_player(self) -> bool:
        if self.player is None or self.player.is_dead:
            return False
        return self._distance_to_player() <= self.stats.sight_range

    def _in_chase_range(self) -> bool:
        if self.player is None or self.player.is_dead:
            return False
        return self._distance_to_player() <= self.stats.lose_range

    # ----------------------------------------------------------------
    # 受击接口
    # ----------------------------------------------------------------

    def take_damage(self, amount: int, knockback_dir: int = 0,
                    poise_damage: float = 10.0):
        if self.fsm.is_in("Dead"):
            return
        actual = self.stats.take_damage(amount)
        if actual > 0:
            self._hit_flash = _HIT_FLASH_DURATION
            if knockback_dir != 0:
                # 通过组件施加击退（同时保留 _knockback_vx 兼容字段）
                self.kb.apply(knockback_dir, 180.0)
                self._knockback_vx = knockback_dir * 180.0

            # 消耗韧性（轻/重攻击由调用方传入不同数值）
            poise_broken = self.stats.consume_poise(poise_damage)
            if poise_broken and not self.fsm.is_in("Dead"):
                from combat.status_effect import StunEffect
                self.status.add(StunEffect())

        if self.stats.is_dead:
            self.fsm.change_state("Dead")
        else:
            self.fsm.change_state("Hurt")

    def _on_bleed_burst(self, burst_dmg: int) -> None:
        """流血爆发回调：产生红色飘字并触发受击闪光。"""
        self._hit_flash = _HIT_FLASH_DURATION
        if hasattr(self.status, "_ftm") and self.status._ftm is not None:
            self.status._ftm.add(
                f"流血 -{burst_dmg}",
                self.rect.centerx,
                self.rect.top - 4,
                color=(220, 30, 30),
                size=16,
            )

    def _on_dot_damage(self, dmg: int, effect_name: str) -> None:
        """持续伤害回调（毒/燃烧）：产生对应颜色的飘字。"""
        _color_map = {
            "poison": (60, 200, 60),
            "burn":   (255, 120, 30),
        }
        color = _color_map.get(effect_name, (200, 200, 60))
        if hasattr(self.status, "_ftm") and self.status._ftm is not None:
            self.status._ftm.add(
                f"-{dmg}",
                self.rect.centerx,
                self.rect.top - 4,
                color=color,
                size=14,
            )

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float, collision_map: "CollisionMap"):
        if not self.active:
            return

        # 保存 collision_map 引用供跳跃探针使用
        self._last_collision_map = collision_map

        # 各计时器
        if self._hit_flash    > 0: self._hit_flash    = max(0.0, self._hit_flash    - dt)
        if self._jump_cooldown > 0: self._jump_cooldown = max(0.0, self._jump_cooldown - dt)

        # 韧性恢复（委托给 EnemyStats.update_poise_regen）
        is_idle = (self.fsm.current_name == "Idle")
        self.stats.update_poise_regen(dt, is_idle)

        # 状态异常每帧更新
        self.status.update(dt)

        # 冰冻/眩晕时锁定状态机（不执行 AI 逻辑）
        if self.frozen or self.stunned:
            self.vel_x = 0.0
        else:
            # 状态机
            self.fsm.update(dt)

        # 击退衰减（通过 KnockbackComponent 取速度）
        kb_vx = self.kb.consume(dt)
        if kb_vx != 0.0:
            self.vel_x = kb_vx
            self._knockback_vx = kb_vx
        else:
            self._knockback_vx = 0.0

        # 重力 + 移动解算
        self.gravity.accumulate(dt)
        new_rect, on_ground, new_vx, new_vy = self.resolver.resolve(
            self.rect, self.vel_x, self.gravity.vel_y,
            dt, collision_map, pass_through_platform=False,
        )
        self.rect          = new_rect
        self.vel_x         = new_vx
        self.gravity.vel_y = new_vy
        self.gravity.set_on_ground(on_ground)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: tuple):
        if not self.active:
            return
        ox, oy      = cam_offset
        screen_rect = self.rect.move(-ox, -oy)
        state       = self.fsm.current_name

        # ---- 本体颜色 ----
        if state == "Dead":
            draw_color = (60, 50, 60)
        elif self._hit_flash > 0:
            draw_color = (255, 255, 255)
        elif state == "Hurt":
            draw_color = (220, 100, 100)
        elif state == "Attack":
            draw_color = tuple(min(255, c + 60) for c in self.color)
        else:
            draw_color = self.color

        pygame.draw.rect(surface, draw_color, screen_rect)

        # ---- 攻击框可视化（三段颜色） ----
        if state == "Attack":
            self._render_attack_box(surface, cam_offset)

        # ---- Alert 状态头顶感叹号 ----
        if state == "Alert":
            self._render_alert_indicator(surface, screen_rect)

        # ---- 眼睛 ----
        eye_x = screen_rect.centerx + (6 if self.facing > 0 else -6)
        eye_y = screen_rect.top + 12
        pygame.draw.circle(surface, WHITE, (eye_x, eye_y), 4)
        pygame.draw.circle(surface, (20, 20, 40), (eye_x + self.facing, eye_y), 2)

        # ---- HP 血条 + 韧性条 ----
        if state != "Dead":
            self._render_hp_bar(surface, screen_rect)
            self._render_poise_bar(surface, screen_rect)

        # ---- 调试碰撞框 ----
        self.render_debug(surface, cam_offset)

    def _render_attack_box(self, surface: pygame.Surface, cam_offset: tuple):
        """根据攻击阶段（前摇/判定/后摇）用不同颜色绘制攻击框。"""
        ox, oy = cam_offset
        atk_rect = self._get_attack_rect().move(-ox, -oy)

        # 获取当前攻击阶段
        cur_state = self.fsm.current
        phase = ATK_PHASE_WINDUP
        if hasattr(cur_state, "atk_phase"):
            phase = cur_state.atk_phase

        if phase == ATK_PHASE_WINDUP:
            fill_color   = _CLR_WINDUP_FILL
            border_color = _CLR_WINDUP_BORDER[:3]   # RGBA → RGB
            border_w     = 2
            # 前摇白框加一圈外描边（更显眼）
            outer = atk_rect.inflate(4, 4)
            pygame.draw.rect(surface, (180, 180, 180), outer, 1)

        elif phase == ATK_PHASE_ACTIVE:
            fill_color   = _CLR_ACTIVE_FILL
            border_color = _CLR_ACTIVE_BORDER
            border_w     = 2
            # 判定帧：脉冲膨胀
            frame = getattr(cur_state, "_frame", 0)
            pulse = 2 if (frame % 4 < 2) else 0
            atk_rect = atk_rect.inflate(pulse * 2, pulse * 2)

        else:  # COOLDOWN
            fill_color   = _CLR_COOLDOWN_FILL
            border_color = _CLR_COOLDOWN_BORDER
            border_w     = 1

        # 半透明填充
        if atk_rect.width > 0 and atk_rect.height > 0:
            overlay = pygame.Surface((atk_rect.width, atk_rect.height), pygame.SRCALPHA)
            overlay.fill(fill_color)
            surface.blit(overlay, atk_rect.topleft)

        # 边框
        pygame.draw.rect(surface, border_color, atk_rect, border_w)

    def _render_hp_bar(self, surface: pygame.Surface, screen_rect: pygame.Rect):
        ratio = self.stats.hp_ratio
        bx    = screen_rect.centerx - BAR_W // 2
        # 血条在实体顶部上方 BAR_OY 像素处（向上）
        by    = screen_rect.top - BAR_OY - BAR_H
        pygame.draw.rect(surface, (60, 60, 60), (bx, by, BAR_W, BAR_H))
        filled = int(BAR_W * ratio)
        if filled > 0:
            r = int(255 * (1.0 - ratio))
            g = int(255 * ratio)
            pygame.draw.rect(surface, (r, g, 0), (bx, by, filled, BAR_H))

    def _render_poise_bar(self, surface: pygame.Surface, screen_rect: pygame.Rect):
        """在血条正下方绘制灰白色韧性条。"""
        max_poise = self.stats.max_poise
        if max_poise <= 0:
            return

        ratio = max(0.0, min(1.0, self.stats.poise / max_poise))

        bx = screen_rect.centerx - BAR_W // 2
        # 韧性条在血条下方 POISE_BAR_GAP 像素
        hp_bar_top = screen_rect.top - BAR_OY - BAR_H
        by = hp_bar_top + BAR_H + POISE_BAR_GAP

        # 背景
        pygame.draw.rect(surface, POISE_CLR_BG,
                         (bx, by, BAR_W, POISE_BAR_H))

        # 前景（韧性偏低时变暗提示玩家即将触发眩晕）
        filled = int(BAR_W * ratio)
        if filled > 0:
            color = POISE_CLR_LOW if ratio < 0.30 else POISE_CLR_FG
            pygame.draw.rect(surface, color,
                             (bx, by, filled, POISE_BAR_H))

    def _render_alert_indicator(self, surface: pygame.Surface,
                                screen_rect: pygame.Rect):
        """Alert 状态在头顶绘制黄色感叹号。"""
        cx = screen_rect.centerx
        top = screen_rect.top - 24
        # 感叹号本体（小竖矩形 + 圆点）
        pygame.draw.rect(surface, (255, 220, 60), (cx - 2, top, 4, 10))
        pygame.draw.rect(surface, (60, 40, 0),    (cx - 2, top, 4, 10), 1)
        pygame.draw.circle(surface, (255, 220, 60), (cx, top + 14), 2)

    # ----------------------------------------------------------------
    # 属性
    # ----------------------------------------------------------------

    @property
    def is_dead(self) -> bool:
        return self.fsm.is_in("Dead") or self.dead

    @property
    def current_state(self) -> str:
        return self.fsm.current_name
