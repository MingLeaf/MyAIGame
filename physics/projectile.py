# =============================================================
# physics/projectile.py —— 抛射物物理系统
#
# 设计：
#   1. Projectile 基类：
#      - 位置 / 速度 / 重力 / 寿命 / 朝向
#      - 自带 Hitbox 用于命中目标
#      - 与 collision_map 进行环境碰撞检测
#      - on_hit / on_environment_hit 回调
#   2. 子类示例：Arrow（弓箭，受重力影响）、MagicBall（直线魔法弹）
#   3. 第 4 阶段先实现物理框架，第 5/7 阶段完善箭矢/魔法弹具体行为
# =============================================================
from __future__ import annotations

import pygame
from typing import Optional, TYPE_CHECKING

from combat.hitbox import Hitbox

if TYPE_CHECKING:
    from map.collision_map import CollisionMap


# 默认参数
DEFAULT_LIFETIME = 3.0      # 抛射物存活时间（秒）
ARROW_GRAVITY    = 600.0    # 箭矢重力（px/s²）
MAGIC_GRAVITY    = 0.0      # 魔法弹通常无重力


class Projectile:
    """
    抛射物基类。

    构造参数：
        x, y         初始位置（中心点）
        vx, vy       初始速度（px/s）
        damage       命中伤害
        owner        发射方（玩家或敌人，用于过滤友军）
        gravity      重力加速度（0 表示直线飞行）
        lifetime     最长存活时间（秒）
        width/height 视觉/碰撞尺寸
        element      攻击元素
        poise_damage 韧性伤害
    """

    color: tuple = (240, 220, 100)  # 默认暖黄色

    def __init__(self,
                 x: float,
                 y: float,
                 vx: float,
                 vy: float,
                 damage: int,
                 owner: Optional[object] = None,
                 *,
                 gravity:      float = 0.0,
                 lifetime:     float = DEFAULT_LIFETIME,
                 width:        int   = 12,
                 height:       int   = 6,
                 element:      str   = "none",
                 poise_damage: float = 5.0,
                 knockback:    float = 100.0,
                 bleed_stack:  float = 0.0,
                 poison_stack: float = 0.0):
        self.x: float  = float(x)
        self.y: float  = float(y)
        self.vx: float = float(vx)
        self.vy: float = float(vy)

        self.width  = width
        self.height = height
        self.rect   = pygame.Rect(int(x - width / 2),
                                  int(y - height / 2),
                                  width, height)

        self.damage:       int   = damage
        self.owner:        Optional[object] = owner
        self.gravity:      float = gravity
        self.lifetime:     float = lifetime
        self.element:      str   = element
        self.poise_damage: float = poise_damage
        self.knockback:    float = knockback
        # 状态积累（第 11 阶段：从武器/物品配置透传）
        self.bleed_stack:  float = bleed_stack
        self.poison_stack: float = poison_stack

        self.alive:   bool = True
        self._age:    float = 0.0
        self._hit_targets: set = set()   # 已命中目标（避免重复结算）

    def update(self,
               dt: float,
               collision_map: Optional["CollisionMap"] = None,
               targets: Optional[list] = None) -> None:
        """
        :param targets: 候选受击对象列表（具有 .rect 属性），命中即调用 on_hit。
        """
        if not self.alive:
            return

        # 寿命检测
        self._age += dt
        if self._age >= self.lifetime:
            self.alive = False
            return

        # 重力 + 位移积分
        self.vy += self.gravity * dt
        self.x  += self.vx * dt
        self.y  += self.vy * dt

        self.rect.x = int(self.x - self.width / 2)
        self.rect.y = int(self.y - self.height / 2)

        # 环境碰撞
        if collision_map is not None and self._check_env_collision(collision_map):
            if self._age > 0.1:
                self.on_environment_hit()
                return

        # 实体命中
        if targets:
            for tgt in targets:
                if not self.alive:
                    break
                if tgt is self.owner:
                    continue
                if id(tgt) in self._hit_targets:
                    continue
                rect = getattr(tgt, "rect", None)
                if rect is None or not self.rect.colliderect(rect):
                    continue
                if getattr(tgt, "is_dead", False):
                    continue
                self._hit_targets.add(id(tgt))
                self.on_hit(tgt)

    # ----------------------------------------------------------------
    # 子类可重写的回调
    # ----------------------------------------------------------------

    def on_hit(self, target) -> None:
        """命中目标时调用。默认：施加伤害 + 状态积累 + 销毁。"""
        import logging
        _log = logging.getLogger(__name__)
        if hasattr(target, "take_damage"):
            kb_dir = 1 if self.vx >= 0 else -1
            _log.debug("Projectile.on_hit: dmg=%d elem=%s target=%s",
                       self.damage, self.element, type(target).__name__)
            try:
                target.take_damage(self.damage, kb_dir,
                                   element=self.element,
                                   poise_damage=self.poise_damage)
            except TypeError:
                try:
                    target.take_damage(self.damage, kb_dir,
                                       poise_damage=self.poise_damage)
                except TypeError:
                    target.take_damage(self.damage, kb_dir)

        # 施加状态积累（bleed / poison + 元素附加）
        if hasattr(target, "status"):
            from combat.status_effect import (
                BleedEffect, PoisonEffect, BurnEffect, FreezeEffect,
            )
            bleed = getattr(self, "bleed_stack", 0.0)
            if bleed > 0:
                if not target.status.has("bleed"):
                    target.status.add(BleedEffect())
                bf = target.status.get("bleed")
                if bf is not None:
                    bf.add_stack(bleed)
            poison = getattr(self, "poison_stack", 0.0)
            if poison > 0:
                if not target.status.has("poison"):
                    target.status.add(PoisonEffect(duration=30.0))
                pf = target.status.get("poison")
                if pf is not None and hasattr(pf, "add_stack"):
                    pf.add_stack(poison)
            # 元素附加（fire/ice）
            elem = self.element
            if elem == "fire" and not target.status.has("burn"):
                target.status.add(BurnEffect(duration=8.0))
            elif elem == "ice" and not target.status.has("freeze"):
                target.status.add(FreezeEffect(duration=2.0))

        self.alive = False

    def on_environment_hit(self) -> None:
        """命中环境（墙壁/地面）时调用。默认：销毁。"""
        import logging
        logging.getLogger(__name__).debug(
            "Projectile.on_environment_hit: pos=(%d,%d) age=%.2f",
            int(self.x), int(self.y), self._age)
        self.alive = False

    # ----------------------------------------------------------------
    # 内部工具
    # ----------------------------------------------------------------

    def _check_env_collision(self, collision_map: "CollisionMap") -> bool:
        """与碰撞地图的实心瓦片进行 AABB 检测。"""
        if not hasattr(collision_map, "get_solid_tiles_in_rect"):
            return False
        tiles = collision_map.get_solid_tiles_in_rect(self.rect)
        return bool(tiles)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        if not self.alive:
            return
        ox, oy = cam_offset
        draw_rect = self.rect.move(-ox, -oy)
        pygame.draw.rect(surface, self.color, draw_rect)
        pygame.draw.rect(surface, (40, 40, 40), draw_rect, 1)

    # ----------------------------------------------------------------
    # 属性
    # ----------------------------------------------------------------

    @property
    def position(self) -> tuple[float, float]:
        return self.x, self.y

    @property
    def age(self) -> float:
        return self._age

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} pos=({self.x:.0f},{self.y:.0f}) "
                f"vel=({self.vx:.0f},{self.vy:.0f}) age={self._age:.2f}/{self.lifetime}>")


# =============================================================
# 子类示例：Arrow（受重力的箭矢）
# =============================================================

class Arrow(Projectile):
    """箭矢：直线初速度 + 弱重力，命中后短暂插着停留。"""

    color = (220, 200, 140)

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 damage: int, owner=None, **kwargs):
        kwargs.setdefault("gravity",  ARROW_GRAVITY)
        kwargs.setdefault("lifetime", 4.0)
        kwargs.setdefault("width",    14)
        kwargs.setdefault("height",   4)
        kwargs.setdefault("element",  "physical")
        kwargs.setdefault("poise_damage", 6.0)
        super().__init__(x, y, vx, vy, damage, owner, **kwargs)


# =============================================================
# 子类示例：MagicBall（无重力直线魔法弹）
# =============================================================

class MagicBall(Projectile):
    """魔法弹：直线飞行不受重力，常用于法师攻击。"""

    color = (140, 180, 255)

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 damage: int, owner=None, *, element="none", **kwargs):
        kwargs.setdefault("gravity",  MAGIC_GRAVITY)
        kwargs.setdefault("lifetime", 2.5)
        kwargs.setdefault("width",    18)
        kwargs.setdefault("height",   18)
        kwargs.setdefault("poise_damage", 8.0)
        super().__init__(x, y, vx, vy, damage, owner, element=element, **kwargs)

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        if not self.alive:
            return
        ox, oy = cam_offset
        cx = int(self.x - ox)
        cy = int(self.y - oy)
        # 双圈叠加，外圈淡色光晕
        radius = max(4, self.width // 2)
        glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 60),
                           (radius * 2, radius * 2), radius * 2)
        surface.blit(glow, (cx - radius * 2, cy - radius * 2))
        pygame.draw.circle(surface, self.color, (cx, cy), radius)
