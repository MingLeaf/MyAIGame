# =============================================================
# combat/hitbox.py —— 攻击判定框（第 4 阶段·统一模块）
#
# 设计目标：
#   1. 作为「玩家 / 敌人 / 抛射物」共用的攻击判定框基础类
#   2. 自身管理生命周期（active_frames 用尽后失效）
#   3. 维护已命中目标集合，避免单帧多次伤害
#   4. 内嵌可视化渲染（前摇 / 判定 / 收尾三段配色）
#   5. 不耦合任何具体实体，由 HitResolver 负责命中解算
#
# 兼容说明：
#   原 entities/player/attack_hitbox.py 仍可使用，
#   现在内部直接继承本类（保持构造参数完全一致）。
# =============================================================
from __future__ import annotations

import pygame
from typing import Optional


# ---- 阶段标识（供渲染层选择配色） ----
PHASE_WINDUP   = "windup"
PHASE_ACTIVE   = "active"
PHASE_COOLDOWN = "cooldown"
PHASE_NONE     = "none"


# ---- 攻击框可视化配色（RGBA） ----
COLOR_ACTIVE_FILL    = (255, 200,  40, 160)
COLOR_ACTIVE_BORDER  = (255, 240,  80)
COLOR_WINDUP_FILL    = (255, 120,  20,  60)
COLOR_WINDUP_BORDER  = (200, 100,  30)
COLOR_COOLDOWN_FILL  = (180,  80,  20,  40)
COLOR_COOLDOWN_BORDER= (160,  70,  20)


class Hitbox:
    """
    通用攻击判定框基类。

    单次攻击在「active 阶段」启用此对象：
      - 在 active_frames 帧数内每帧调用 update()
      - HitResolver 用 rect 与目标做矩形重叠检测
      - can_hit / register_hit 防止单次攻击对同一目标多次伤害
      - 失效后 active=False，外层应将其从列表清理

    构造参数采用「中心 + 偏移」方式定位，
    自动根据 facing 计算实际 rect 位置。
    """

    def __init__(self,
                 owner_rect: pygame.Rect,
                 facing: int,
                 offset_x: int,
                 offset_y: int,
                 width: int,
                 height: int,
                 damage: int,
                 active_frames: int,
                 *,
                 knockback:      float = 180.0,
                 stamina_damage: float = 20.0,
                 element:        str   = "none",
                 poise_damage:   float = 10.0,
                 bleed_stack:    float = 0.0,
                 poison_stack:   float = 0.0,
                 source: Optional[object] = None):
        # 计算 rect（基于 owner 中心 + facing 方向）
        cx = owner_rect.centerx + facing * offset_x
        cy = owner_rect.centery + offset_y
        self.rect = pygame.Rect(cx - width // 2, cy - height // 2, width, height)
        self._base_rect = self.rect.copy()

        # 数值
        self.damage          = damage
        self.knockback       = knockback
        self.stamina_damage  = stamina_damage
        self.element         = element
        self.poise_damage    = poise_damage
        self.bleed_stack     = bleed_stack
        self.poison_stack    = poison_stack
        self.facing          = facing

        # 命中来源（可指向 Player / Enemy / Projectile，用于背刺判定等）
        self.source = source

        # 生命周期
        self._total_frames: int = active_frames
        self._frames_left:  int = active_frames
        self.active:        bool = True

        # 已命中过的目标 id 集合（防止单帧多次伤害）
        self._hit_targets: set = set()

        # 已经过的判定帧数（脉冲渲染用）
        self._frame: int = 0

    # ----------------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------------

    def update(self) -> None:
        """每帧调用一次：递减剩余帧数。"""
        if self._frames_left > 0:
            self._frames_left -= 1
            self._frame       += 1
        else:
            self.active = False

    @property
    def in_active_window(self) -> bool:
        """当前是否处于伤害判定窗口（存活期间均算判定帧）。"""
        return self.active and self._frames_left > 0

    @property
    def phase(self) -> str:
        """简易阶段标识（默认仅 active / none）。子类可重写。"""
        return PHASE_ACTIVE if self.in_active_window else PHASE_NONE

    # ----------------------------------------------------------------
    # 命中记录
    # ----------------------------------------------------------------

    def can_hit(self, target_id: int) -> bool:
        return target_id not in self._hit_targets

    def register_hit(self, target_id: int) -> None:
        self._hit_targets.add(target_id)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        """绘制判定框（半透明填充 + 边框 + 脉冲缩放）。"""
        if not self.active:
            return
        ox, oy    = cam_offset
        draw_rect = self.rect.move(-ox, -oy)

        in_win = self.in_active_window
        if in_win:
            pulse = 2 if (self._frame % 4 < 2) else 0
            vis_rect     = draw_rect.inflate(pulse * 2, pulse * 2)
            fill_color   = COLOR_ACTIVE_FILL
            border_color = COLOR_ACTIVE_BORDER
        else:
            vis_rect     = draw_rect
            fill_color   = COLOR_WINDUP_FILL
            border_color = COLOR_WINDUP_BORDER

        if vis_rect.width > 0 and vis_rect.height > 0:
            overlay = pygame.Surface((vis_rect.width, vis_rect.height),
                                     pygame.SRCALPHA)
            overlay.fill(fill_color)
            surface.blit(overlay, vis_rect.topleft)
        pygame.draw.rect(surface, border_color, vis_rect, 2)

    # 调试别名（保持与旧 AttackHitbox 接口一致）
    def render_debug(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        self.render(surface, cam_offset)


# =============================================================
# 兼容别名：原 AttackHitbox 直接对应本类
# =============================================================
AttackHitbox = Hitbox
