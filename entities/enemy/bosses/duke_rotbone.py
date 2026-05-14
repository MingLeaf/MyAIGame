# =============================================================
# entities/enemy/bosses/duke_rotbone.py —— 腐骨公爵
#
# Boss①：古墓地带领主。
#
# 一阶段技能：
#   1. 骨刃斩 — 中距离横斩
#   2. 毒雾吐息 — 前方扇形毒雾 + 中毒积累
#   3. 召唤骷髅 — 召唤 2 名不死骷髅（skeleton ally type）
#
# 二阶段（HP ≤ 50%）：
#   速度 +30%，攻击 +20%
#   新增技能：毒沼 — 地面生成持续毒池
#
# 复活：
#   首次死亡 → 3 秒后满血复活（60% HP）→ 需二次击杀
#
# 击败掉落：
#   灵核 "腐骨之灵" + 解锁 area_swamp
# =============================================================
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from entities.enemy.bosses.base_boss import BaseBoss
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


class DukeRotbone(BaseBoss):
    """腐骨公爵。"""

    CATEGORY = "duke_rotbone"

    def __init__(self, x: float, y: float):
        super().__init__(x, y, w=48, h=64, color=(100, 160, 80))
        self.load_boss_data("duke_rotbone")
        self._summon_cd: float = 0.0

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float, collision_map) -> None:
        super().update(dt, collision_map)

        # 技能选择（简单的 CD 驱动 + 玩家距离判断）
        if self.player is None or self.dead or self._revive_pending:
            return

        dist = self._dist_to_player()

        # 如果正在施法中则不打断
        if self._current_skill is not None:
            self.update_skill_cast(dt)
            # 技能判定
            hb = self.get_skill_hitbox()
            if hb is not None and self.player is not None:
                self._apply_skill_hitbox(hb)
            return

        # 选择技能
        self._select_and_cast_skill(dist)

    # ----------------------------------------------------------------
    # 技能选择
    # ----------------------------------------------------------------

    def _select_and_cast_skill(self, dist: float) -> None:
        """根据距离和 CD 选择最优技能。"""
        # 0: 骨刃斩（近），1: 毒雾吐息（中），2: 召唤骷髅（任意），3: 毒沼（二阶段专属）
        # 优先顺序：召唤 > 毒雾 > 骨刃 > 毒沼

        if self.try_cast_skill(2):   # 召唤
            return
        if dist < 120 and self.try_cast_skill(0):  # 近战骨刃
            return
        if 80 < dist < 250 and self.try_cast_skill(1):  # 毒雾
            return
        if self._phase == 2 and self.try_cast_skill(3):  # 毒沼
            return
        # 兜底近战
        if self.try_cast_skill(0):
            return

    # ----------------------------------------------------------------
    # 召唤骷髅
    # ----------------------------------------------------------------

    def _do_summon(self) -> None:
        """生成 2 名不死骷髅友军。"""
        event_manager.emit("boss_summon_minions", {
            "boss": self,
            "count": 2,
            "minion_type": "undead",
            "x": self.rect.centerx,
            "y": self.rect.bottom - 32,
        })

    # ----------------------------------------------------------------
    # 技能命中处理
    # ----------------------------------------------------------------

    def _apply_skill_hitbox(self, hb) -> None:
        """将技能判定框施加到玩家。"""
        if self.player is None:
            return
        if not hb.rect.colliderect(self.player.rect):
            return

        sk = self._current_skill
        if sk is None:
            return

        # 伤害
        damage = int(self.stats.atk * sk.damage_mult)
        self.player.take_damage(
            damage,
            knockback_dir=self._facing,
            element=sk.element,
            poise_damage=sk.poise_damage,
        )

        # 状态积累
        if sk.status_buildup:
            self._apply_status(sk)

        hb.active_frames = 0  # 单次命中

    def _apply_status(self, sk) -> None:
        """对玩家施加状态异常积累。"""
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
