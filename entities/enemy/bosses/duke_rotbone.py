# =============================================================
# entities/enemy/bosses/duke_rotbone.py —— 腐骨公爵
#
# Boss①：古墓地带领主。
#
# 一阶段技能：
#   1. 骨刃斩 — 中距离横斩
#   2. 毒雾吐息 — 前方扇形毒雾 + 中毒积累
#   3. 召唤骷髅 — 召唤 2 名不死骷髅
#
# 召唤规则：
#   - 场上最多同时存在 2 只小兵
#   - 所有小兵死亡后进入 10 秒冷却
#   - 冷却结束后可再次召唤（Boss 静止施法 2 秒 → 显示进度条）
#
# 二阶段（HP ≤ 50%）：
#   速度 +30%，攻击 +20%
#   新增技能：毒沼 — 地面生成持续毒池
#
# 复活：首次死亡 → 3 秒后复活（60% HP）→ 需二次击杀
# =============================================================
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import pygame

from entities.enemy.bosses.base_boss import BaseBoss
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


class DukeRotbone(BaseBoss):
    """腐骨公爵。"""

    CATEGORY = "duke_rotbone"

    SUMMON_COOLDOWN   = 10.0   # 小兵全灭后冷却
    SUMMON_WINDUP     = 2.0    # 施法读条时间
    MAX_MINIONS       = 2      # 最大同时存在数

    def __init__(self, x: float, y: float):
        super().__init__(x, y, w=48, h=64, color=(100, 160, 80))
        self.load_boss_data("duke_rotbone")
        self._summon_cooldown: float = 0.0
        self._current_area = None  # 由 BossScene 设置

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float, collision_map) -> None:
        super().update(dt, collision_map)

        if self.player is None or self.dead or self._revive_pending or self.stunned:
            return

        # 推进召唤冷却
        if self._summon_cooldown > 0:
            self._summon_cooldown -= dt

        dist = self._dist_to_player()

        # 如果正在施法中则不打断
        if self._current_skill is not None:
            just_active = self.update_skill_cast(dt)
            if just_active:
                sk = self._current_skill
                if sk.skill_id == "summon_skeleton":
                    self._do_summon()
                    # 召唤完成后进入冷却
                    self._summon_cooldown = 0  # 重置（等小兵死完再计）
                else:
                    hb = self.get_skill_hitbox()
                    if hb is not None and self.player is not None:
                        self._apply_skill_hitbox(hb)
            return

        # 选择技能
        self._select_and_cast_skill(dist)

    # ----------------------------------------------------------------
    # 技能选择（召唤带约束）
    # ----------------------------------------------------------------

    def _select_and_cast_skill(self, dist: float) -> None:
        """根据距离、CD、召唤限制选择最优技能。"""
        # 0: 骨刃斩（近），1: 毒雾吐息（中），2: 召唤骷髅，3: 毒沼（二阶段）

        # 召唤优先，但受规则约束
        if self._can_summon() and self.try_cast_skill(2):
            return
        if dist < 120 and self.try_cast_skill(0):
            return
        if 80 < dist < 250 and self.try_cast_skill(1):
            return
        if self._phase == 2 and self.try_cast_skill(3):
            return
        if self.try_cast_skill(0):
            return

    def _can_summon(self) -> bool:
        """是否允许召唤：冷却结束 + 场上无存活小兵。"""
        if self._summon_cooldown > 0:
            return False
        alive = self._count_alive_minions()
        return alive == 0

    def _count_alive_minions(self) -> int:
        """统计 Boss 召唤的小兵存活数（通过 area.enemies 中 team=enemy 且非 boss）。"""
        area = self._current_area
        if area is None:
            return 0
        count = 0
        for e in getattr(area, "enemies", []):
            if e is self or getattr(e, "dead", False):
                continue
            if getattr(e, "team", "enemy") == "enemy":
                count += 1
        return count

    # ----------------------------------------------------------------
    # 重写 try_cast_skill：召唤技能使用自定义前摇
    # ----------------------------------------------------------------

    def try_cast_skill(self, skill_index: int) -> bool:
        """尝试释放技能。召唤技能使用 2 秒前摇。"""
        if skill_index < 0 or skill_index >= len(self._skills):
            return False
        sk = self._skills[skill_index]
        if sk._cd_left > 0.0:
            return False
        if self._current_skill is not None:
            return False

        self._current_skill = sk
        # 召唤技能：使用自定义 SUMMON_WINDUP
        if sk.skill_id == "summon_skeleton":
            self._skill_timer = self.SUMMON_WINDUP
        else:
            self._skill_timer = sk.windup_frames / 60.0
        self._skill_active = False
        return True

    # ----------------------------------------------------------------
    # 召唤骷髅
    # ----------------------------------------------------------------

    def _do_summon(self) -> None:
        """生成 2 名不死骷髅，加入冷却管理。"""
        event_manager.emit("boss_summon_minions", {
            "boss": self,
            "count": self.MAX_MINIONS,
            "minion_type": "undead",
            "x": self.rect.centerx,
            "y": self.rect.bottom - 32,
        })

    # ----------------------------------------------------------------
    # 小兵死亡回调（由场景调用）
    # ----------------------------------------------------------------

    def on_minion_died(self) -> None:
        """当一只小兵死亡时调用。全部死亡后启动 10 秒冷却。"""
        alive = self._count_alive_minions()
        if alive == 0:
            self._summon_cooldown = self.SUMMON_COOLDOWN

    # ----------------------------------------------------------------
    # 渲染（含召唤进度条）
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        super().render(surface, cam_offset)

        # 召唤读条：Boss 头顶显示进度条
        if self._current_skill is not None and self._current_skill.skill_id == "summon_skeleton":
            if not self._skill_active:
                self._render_summon_progress(surface, cam_offset)

    def _render_summon_progress(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        """召唤施法进度条（Boss 头顶蓝色）。"""
        ox, oy = cam_offset
        # 屏幕坐标
        sx = int(self.rect.centerx) - ox
        sy = int(self.rect.top) - oy - 24

        bar_w = 48
        bar_h = 6
        bx = sx - bar_w // 2
        by = sy

        # 进度 = 1 - timer/max_timer
        if self._skill_timer > 0 and self.SUMMON_WINDUP > 0:
            progress = 1.0 - (self._skill_timer / self.SUMMON_WINDUP)
        else:
            progress = 0.0

        # 背景
        pygame.draw.rect(surface, (40, 40, 50), (bx, by, bar_w, bar_h))
        # 填充（蓝色）
        if progress > 0:
            fill_w = int(bar_w * progress)
            pygame.draw.rect(surface, (80, 140, 255), (bx, by, fill_w, bar_h))
        # 边框
        pygame.draw.rect(surface, (120, 160, 255), (bx, by, bar_w, bar_h), 1)

        # 标签
        from ui.font_manager import get_font
        font = get_font(11)
        label = font.render("召唤中", True, (180, 200, 255))
        surface.blit(label, (bx + bar_w + 4, by - 1))

    # ----------------------------------------------------------------
    # 技能命中处理
    # ----------------------------------------------------------------

    def _apply_skill_hitbox(self, hb) -> None:
        if self.player is None:
            return
        if not hb.rect.colliderect(self.player.rect):
            return

        sk = self._current_skill
        if sk is None:
            return

        damage = int(self.stats.atk * sk.damage_mult)
        self.player.take_damage(
            damage,
            knockback_dir=self._facing,
            attacker=self,
            element=sk.element,
            poise_damage=sk.poise_damage,
        )

        if sk.status_buildup:
            self._apply_status(sk)

    def _apply_status(self, sk) -> None:
        buildup = sk.status_buildup
        stype = buildup.get("type", "")
        value = buildup.get("value", 0.0)
        if stype == "poison" and self.player is not None:
            event_manager.emit("player_status_buildup", {
                "type": "poison",
                "value": value,
                "source": self,
            })

    # ----------------------------------------------------------------
    # 辅助
    # ----------------------------------------------------------------

    def _dist_to_player(self) -> float:
        if self.player is None:
            return 9999.0
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        return (dx * dx + dy * dy) ** 0.5

    @property
    def _facing(self) -> int:
        if self.player is None:
            return 1
        return 1 if self.player.rect.centerx > self.rect.centerx else -1

    # ----------------------------------------------------------------
    # 属性
    # ----------------------------------------------------------------

    @property
    def drop_table(self):
        from combat.drop_system import DropEntry
        boss_data = self._boss_data
        soul = boss_data.get("boss_soul", {})
        return [
            DropEntry(
                item_id=soul.get("item_id", "boss_soul_duke"),
                chance=1.0,
                qty_min=1,
                qty_max=1,
            ),
        ]

    def get_dropped_soul_item(self) -> dict:
        return self._boss_data.get("boss_soul", {})


__all__ = ["DukeRotbone"]
