# =============================================================
# systems/soul_fragment_system.py —— 灵魂碎片系统
#
# 第 8 阶段：类魂核心机制 —— 灵魂碎片的获取、掉落、遗物生成、
# 捡回、永久消失。
#
# 规则（game_rule.md §9.1）：
#   - 击败敌人 → 获得灵魂碎片（自动计入玩家 soul_fragments）
#   - 死亡 → 在死亡位置生成 DeathRelic（含当前全部灵魂碎片）
#          → 玩家 soul_fragments 归零 → 营地复活
#   - 走到 DeathRelic → 捡回全部灵魂碎片
#   - 再次死亡（未捡回）→ 旧遗物消失，新遗物仅在死亡位置生成
#                         （含第二次死亡时所持的碎片数，旧碎片永久消失）
#
# DeathRelic：是一个轻量实体（存于 area.death_relic），带渲染。
# =============================================================
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import pygame
import math
import random

from utils.color import UI_HIGHLIGHT, WHITE
from utils.timer import Timer
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player
    from map.area import Area


# ---- DeathRelic 实体 ----

class DeathRelic:
    """
    玩家死亡后在地图中生成的遗物。
    含灵魂碎片数量 + 位置，可被玩家碰撞拾取。

    视觉效果：脉动光球（金色 / 绿色渐变），大小随灵魂量波动。
    """

    RADIUS_BASE = 14          # 基础半径
    RADIUS_MAX  = 28          # 最大半径
    PICKUP_RADIUS = 32        # 拾取触发半径

    def __init__(self, x: float, y: float, soul_count: int):
        self.x = x
        self.y = y
        self.soul_count = soul_count

        # 渲染
        self._anim_timer = Timer(0.06, auto_reset=True)
        self._anim_phase = random.random() * math.pi * 2
        self._glow_offset = 0.0

        # 碰撞矩形
        r = self.RADIUS_MAX
        self.rect = pygame.Rect(
            int(x - r), int(y - r), r * 2, r * 2
        )
        self.pickup_rect = pygame.Rect(
            int(x - self.PICKUP_RADIUS),
            int(y - self.PICKUP_RADIUS),
            self.PICKUP_RADIUS * 2,
            self.PICKUP_RADIUS * 2,
        )

    def update(self, dt: float) -> None:
        self._anim_timer.update(dt)

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        ox, oy = cam_offset
        sx = int(self.x) - ox
        sy = int(self.y) - oy

        # 脉动半径
        phase = math.sin(pygame.time.get_ticks() * 0.004 + self._anim_phase)
        r = self.RADIUS_BASE + (self.RADIUS_MAX - self.RADIUS_BASE) * (phase * 0.5 + 0.5)

        # 外层光晕
        glow_colors = [
            (255, 200, 60, 30),
            (220, 255, 80, 25),
            (255, 180, 40, 20),
        ]
        for i, col in enumerate(glow_colors):
            glow_r = r + 6 + i * 3
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, col, (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        # 核心光球
        pygame.draw.circle(surface, (240, 210, 40), (sx, sy), r)
        pygame.draw.circle(surface, (255, 255, 160), (sx, sy), r * 0.5)

        # 绿色微光（灵魂色）
        green_r = r * 0.6
        green_surf = pygame.Surface((int(green_r * 2), int(green_r * 2)), pygame.SRCALPHA)
        pygame.draw.circle(green_surf, (100, 240, 140, 100),
                          (int(green_r), int(green_r)), int(green_r))
        surface.blit(green_surf, (sx - green_r, sy - green_r))

        # 灵魂数量文字
        from ui.font_manager import get_font
        font = get_font(13)
        text = font.render(f"{self.soul_count}", True, (255, 255, 220))
        surface.blit(text, text.get_rect(center=(sx, sy + r + 10)))


# ---- 灵魂碎片系统 ----

class SoulFragmentSystem:
    """
    灵魂碎片管理器（全静态方法）。

    核心状态绑定在 player.soul_fragments 上，DeathRelic 绑定在 Area 上。
    """

    # 敌人死亡掉落灵魂碎片的基础量（随后乘以等级系数）
    BASE_SOUL_DROP = 30

    # 掉落碎片量的等级系数
    LEVEL_MULTIPLIER = 0.25    # 每级 +25%
    MIN_SOUL_DROP   = 10

    # ----------------------------------------------------------------
    # 敌人死亡 → 掉落灵魂碎片
    # ----------------------------------------------------------------

    @staticmethod
    def grant_for_enemy(player: "Player", enemy) -> int:
        """
        敌人死亡时，计算并增加玩家的灵魂碎片数。
        返回实际增加的碎片量。

        :param player: 玩家实例
        :param enemy:  被击败的敌人实例
        """
        if player is None or enemy is None:
            return 0

        # 基础量
        base = SoulFragmentSystem.BASE_SOUL_DROP

        # 敌人等级倍率
        level = getattr(enemy, "level", 1)
        multiplier = 1.0 + (level - 1) * SoulFragmentSystem.LEVEL_MULTIPLIER

        # 敌方类型加成
        cat = getattr(enemy, "CATEGORY", "infantry")
        cat_multiplier = {
            "infantry":    1.0,
            "heavy_armor": 1.4,
            "archer":      1.1,
            "mage":        1.3,
            "undead":      1.0,
            "beast":       1.2,
            "elite":       2.5,
        }.get(cat, 1.0)

        amount = max(SoulFragmentSystem.MIN_SOUL_DROP,
                     int(base * multiplier * cat_multiplier))

        # 增加玩家灵魂碎片
        current = getattr(player, "soul_fragments", 0)
        player.soul_fragments = current + amount

        # 事件广播
        event_manager.emit("soul_fragments_changed", {
            "amount":   amount,
            "total":    player.soul_fragments,
            "source":   "enemy",
            "enemy_id": getattr(enemy, "CATEGORY", "unknown"),
        })

        return amount

    # ----------------------------------------------------------------
    # 玩家死亡 → 生成遗物
    # ----------------------------------------------------------------

    @staticmethod
    def create_death_relic(player: "Player", area: Optional["Area"]) -> Optional[DeathRelic]:
        """
        玩家死亡时调用：
          1. 保存当前灵魂碎片数
          2. 在死亡位置创建 DeathRelic
          3. 将玩家灵魂碎片清零
          4. 之前存在的旧遗物（若有）自动消失

        返回新建的 DeathRelic，若 area 为 None 则返回 None。
        """
        if player is None or area is None:
            return None

        soul_count = getattr(player, "soul_fragments", 0)

        # 清除旧遗物
        old_relic = getattr(area, "death_relic", None)
        if old_relic is not None:
            area.death_relic = None

        # 如果没有任何灵魂碎片，不生成遗物
        if soul_count <= 0:
            player.soul_fragments = 0
            return None

        # 创建新遗物
        relic = DeathRelic(
            x=player.rect.centerx,
            y=player.rect.centery,
            soul_count=soul_count,
        )

        # 绑定到区域
        area.death_relic = relic

        # 玩家碎片清零
        player.soul_fragments = 0

        # 事件广播
        event_manager.emit("death_relic_spawned", {
            "x":          relic.x,
            "y":          relic.y,
            "soul_count": soul_count,
        })

        event_manager.emit("soul_fragments_changed", {
            "amount": -soul_count,
            "total":  0,
            "source":  "death",
        })

        return relic

    # ----------------------------------------------------------------
    # 遗物捡回
    # ----------------------------------------------------------------

    @staticmethod
    def try_pickup_relic(player: "Player", area: Optional["Area"]) -> int:
        """
        每帧检测：玩家是否走入 DeathRelic 范围。
        若在范围内，捡回灵魂碎片。

        返回捡回的碎片数，若未捡回返回 0。
        """
        if player is None or area is None:
            return 0

        relic = getattr(area, "death_relic", None)
        if relic is None:
            return 0

        if not relic.pickup_rect.colliderect(player.rect):
            return 0

        # 捡回
        recovered = relic.soul_count
        current = getattr(player, "soul_fragments", 0)
        player.soul_fragments = current + recovered

        # 清除遗物
        area.death_relic = None

        # 事件广播
        event_manager.emit("death_relic_recovered", {
            "amount": recovered,
            "total":  player.soul_fragments,
        })
        event_manager.emit("soul_fragments_changed", {
            "amount": recovered,
            "total":  player.soul_fragments,
            "source": "relic_recovery",
        })

        return recovered


__all__ = ["SoulFragmentSystem", "DeathRelic"]
