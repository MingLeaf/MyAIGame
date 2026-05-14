# =============================================================
# entities/enemy/bosses/base_boss.py —— Boss 基类
#
# 第 9 阶段：所有 Boss 的共同基类。
#
# 特性：
#   - 两阶段机制：HP ≤ 阈值自动进入二阶段（速度/攻击加成 + 新技能解锁）
#   - 复活机制：首次死亡后可复活一次（如腐骨公爵）
#   - 专属血条渲染数据
#   - 技能系统：每个技能有前摇/冷却/判定框
#   - 死亡事件：boss_killed 派发，掉落灵核
# =============================================================
from __future__ import annotations
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import pygame

from entities.enemy.base_enemy import BaseEnemy
from entities.enemy.enemy_stats import EnemyStats
from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player
    from combat.hitbox import AttackHitbox


class BossSkill:
    """Boss 单个技能的数据快照。"""

    def __init__(self, cfg: dict):
        self.skill_id:   str   = cfg.get("id", "unknown")
        self.name:       str   = cfg.get("name", "技能")
        self.damage_mult:  float = float(cfg.get("damage_mult", 1.0))
        self.knockback:    float = float(cfg.get("knockback", 150.0))
        self.poise_damage: float = float(cfg.get("poise_damage", 20.0))
        self.cooldown:     float = float(cfg.get("cooldown", 2.0))
        self.windup_frames: int  = int(cfg.get("windup_frames", 15))
        self.active_frames: int  = int(cfg.get("active_frames", 8))
        self.hitbox: dict        = cfg.get("hitbox", {})
        self.element:      str   = cfg.get("element", "physical")
        self.status_buildup: Optional[dict] = cfg.get("status_buildup")

        # 运行时
        self._cd_left: float = 0.0


class BaseBoss(BaseEnemy):
    """
    Boss 基类。
    """

    CATEGORY = "boss"

    # ----------------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------------

    def __init__(self, x: float, y: float,
                 w: int = 48, h: int = 64,
                 color: tuple = (140, 60, 60)):
        super().__init__(x, y, width=w, height=h)
        self._boss_data:   dict = {}
        self._skills:      List[BossSkill] = []
        self._phase:       int = 1              # 1 or 2
        self._phase_triggered: bool = False
        self._revived:     bool = False         # 是否已复活
        self._revive_pending: bool = False
        self._revive_timer: float = 0.0

        # 当前激活技能
        self._current_skill: Optional[BossSkill] = None
        self._skill_timer: float = 0.0           # 前摇计时
        self._skill_active: bool = False

        # 自定颜色
        self._boss_color = color

    # ----------------------------------------------------------------
    # 加载配置
    # ----------------------------------------------------------------

    def load_boss_data(self, boss_id: str) -> None:
        """从 data/entities/bosses/{boss_id}.json 加载配置。"""
        from utils.json_loader import load_from_data_dir

        cfg = load_from_data_dir(f"entities/bosses/{boss_id}.json")
        self._boss_data = cfg

        # 渲染
        render = cfg.get("render", {})
        self._boss_color = tuple(render.get("color", [140, 60, 60]))

        # 数值（注入 stats）
        stats = cfg.get("stats", {})
        self.stats = EnemyStats()
        self.stats.max_hp          = int(stats.get("max_hp", 800))
        self.stats.hp              = self.stats.max_hp
        self.stats.atk             = int(stats.get("atk", 30))
        self.stats.defense         = int(stats.get("defense", 15))
        self.stats.speed           = float(stats.get("speed", 100.0))
        self.stats.sight_range     = float(stats.get("sight_range", 500.0))
        self.stats.attack_range    = float(stats.get("attack_range", 80.0))
        self.stats.patrol_radius   = float(stats.get("patrol_radius", 0.0))
        self.stats.max_poise       = float(stats.get("max_poise", 80.0))
        self.stats.bleed_threshold = float(stats.get("bleed_threshold", 200.0))

        # 元素标签
        self.stats.element_tags = stats.get("element_tags", ["boss"])
        self.stats.weaknesses   = stats.get("weaknesses", [])
        self.stats.resistances  = stats.get("resistances", [])
        self.stats.immunities   = stats.get("immunities", [])

        # 技能
        self._skills = [BossSkill(s) for s in cfg.get("skills", [])]

        # 二阶段
        self._phase_two_cfg = cfg.get("phase_two", {})
        self._revive_cfg = cfg.get("revive", {})

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float, collision_map) -> None:
        """Boss 每帧更新（含技能冷却推进）。"""
        if self.dead and not self._revive_pending:
            if self._check_revive():
                return
            super().update(dt, collision_map)
            return

        # 复活倒计时
        if self._revive_pending:
            self._revive_timer -= dt
            if self._revive_timer <= 0.0:
                self._do_revive()
            return

        # 技能冷却推进
        for sk in self._skills:
            if sk._cd_left > 0.0:
                sk._cd_left = max(0.0, sk._cd_left - dt)

        super().update(dt, collision_map)

        # 二阶段检测
        if not self._phase_triggered and self.stats.hp_ratio <= self._phase_two_cfg.get("hp_threshold_pct", 0.5):
            self._enter_phase_two()

    # ----------------------------------------------------------------
    # 二阶段
    # ----------------------------------------------------------------

    def _enter_phase_two(self) -> None:
        self._phase = 2
        self._phase_triggered = True

        cfg = self._phase_two_cfg
        self.stats.speed *= float(cfg.get("speed_mult", 1.3))
        self.stats.atk = int(self.stats.atk * float(cfg.get("atk_mult", 1.2)))

        event_manager.emit("boss_phase_change", {
            "boss": self,
            "phase": 2,
            "boss_id": self._boss_data.get("id", ""),
        })

    @property
    def phase(self) -> int:
        return self._phase

    @property
    def boss_hp_ratio(self) -> float:
        return self.stats.hp_ratio

    @property
    def boss_display_name(self) -> str:
        return self._boss_data.get("display_name", "Boss")

    @property
    def boss_title(self) -> str:
        return self._boss_data.get("title", "")

    # ----------------------------------------------------------------
    # 复活
    # ----------------------------------------------------------------

    def _check_revive(self) -> bool:
        """检查是否可复活。返回 True 表示进入复活等待。"""
        if self._revived or not self._revive_cfg:
            return False
        self._revive_pending = True
        self._revive_timer = self._revive_cfg.get("revive_delay", 3.0)
        event_manager.emit("boss_revive_begin", {
            "boss": self,
            "boss_id": self._boss_data.get("id", ""),
            "delay": self._revive_timer,
        })
        return True

    def _do_revive(self) -> None:
        self._revived = True
        self._revive_pending = False
        self.dead = False

        pct = self._revive_cfg.get("revive_hp_pct", 0.6)
        self.stats.hp = int(self.stats.max_hp * pct)

        event_manager.emit("boss_revived", {
            "boss": self,
            "boss_id": self._boss_data.get("id", ""),
            "hp": self.stats.hp,
        })

    # ----------------------------------------------------------------
    # 死亡
    # ----------------------------------------------------------------

    def on_death(self) -> None:
        """Boss 死亡处理。可能触发复活检查。"""
        if self._check_revive():
            return

        # 真正死亡
        super().on_death()
        self._emit_boss_killed()

    def _emit_boss_killed(self) -> None:
        boss_id = self._boss_data.get("id", "")
        event_manager.emit("boss_killed", {
            "boss_id": boss_id,
            "boss": self,
        })

    # ----------------------------------------------------------------
    # 攻击（由 AI 状态驱动）
    # ----------------------------------------------------------------

    def try_cast_skill(self, skill_index: int) -> bool:
        """尝试释放技能。返回 True 表示开始施法前摇。"""
        if skill_index < 0 or skill_index >= len(self._skills):
            return False
        sk = self._skills[skill_index]
        if sk._cd_left > 0.0:
            return False
        self._current_skill = sk
        self._skill_timer = sk.windup_frames / 60.0
        self._skill_active = False
        return True

    def update_skill_cast(self, dt: float) -> bool:
        """
        每帧推进技能施法。
        返回 True 表示需要生成判定框。
        """
        if self._current_skill is None:
            return False
        self._skill_timer -= dt
        if self._skill_timer <= 0 and not self._skill_active:
            self._skill_active = True
            self._skill_timer = self._current_skill.active_frames / 60.0
            return True
        if self._skill_active and self._skill_timer <= 0:
            # 技能结束
            sk = self._current_skill
            sk._cd_left = sk.cooldown
            self._current_skill = None
            self._skill_active = False
        return False

    def get_skill_hitbox(self) -> Optional["AttackHitbox"]:
        """获取当前技能的判定框。"""
        if self._current_skill is None or not self._skill_active:
            return None
        from combat.hitbox import AttackHitbox

        sk = self._current_skill
        hb_data = sk.hitbox
        damage = int(self.stats.atk * sk.damage_mult)

        return AttackHitbox(
            owner_rect=self.rect,
            facing=self._facing,
            offset_x=hb_data.get("offset_x", 30),
            offset_y=hb_data.get("offset_y", -10),
            width=hb_data.get("w", 70),
            height=hb_data.get("h", 50),
            damage=max(1, damage),
            active_frames=sk.active_frames,
            knockback=sk.knockback,
            element=sk.element,
            poise_damage=sk.poise_damage,
            source=self,
        )

    @property
    def is_casting(self) -> bool:
        """是否正在施法（前摇或判定中）。"""
        return self._current_skill is not None

    @property
    def is_skill_active(self) -> bool:
        """判定帧是否激活（此时造成伤害）。"""
        return self._skill_active and self._current_skill is not None

    def _get_attack_rect(self) -> pygame.Rect:
        """获取攻击判定框世界坐标（用于渲染可视化）。"""
        if self._current_skill is None:
            return pygame.Rect(0, 0, 0, 0)
        sk = self._current_skill
        hb = sk.hitbox
        facing = self._facing
        ow = self.rect.width
        oh = self.rect.height

        if facing > 0:
            ax = self.rect.x + ow + hb.get("offset_x", 30) - 30
        else:
            ax = self.rect.x - hb.get("offset_x", 30) - hb.get("w", 70) + 30
        ay = self.rect.y + hb.get("offset_y", -10)
        aw = hb.get("w", 70)
        ah = hb.get("h", 50)
        return pygame.Rect(int(ax), int(ay), aw, ah)

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: tuple) -> None:
        ox, oy = cam_offset
        sx = int(self.rect.x) - ox
        sy = int(self.rect.y) - oy

        # 二阶段颜色变化
        color = self._boss_color
        if self._phase == 2:
            color = tuple(min(255, c + 60) for c in color)

        # Boss 更大矩形
        pygame.draw.rect(surface, color,
                         (sx, sy, self.rect.width, self.rect.height))
        # 描边
        pygame.draw.rect(surface, (255, 255, 255),
                         (sx, sy, self.rect.width, self.rect.height), 2)

        # 二阶段标记
        if self._phase == 2:
            pygame.draw.circle(surface, (255, 60, 60),
                               (sx + self.rect.width // 2, sy - 10), 6)

        # 复活倒计时
        if self._revive_pending:
            import math
            bar_w = 40
            bar_h = 6
            progress = 1.0 - self._revive_timer / self._revive_cfg.get("revive_delay", 3.0)
            bx = sx + (self.rect.width - bar_w) // 2
            by = sy - 18
            pygame.draw.rect(surface, (40, 40, 40), (bx, by, bar_w, bar_h))
            pygame.draw.rect(surface, (0, 200, 100),
                             (bx, by, int(bar_w * progress), bar_h))


__all__ = ["BaseBoss", "BossSkill"]
