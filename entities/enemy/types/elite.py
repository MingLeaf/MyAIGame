# =============================================================
# entities/enemy/types/elite.py —— 精英兵（mini-boss 级）
#
# 数据来源：data/entities/enemies/elite.json
#
# 特征：
#   - 高血量、高韧性、高攻击力
#   - 两个独特技能：
#       1. charge_slash —— 蓄力斩：长前摇 + 巨大伤害 + 远距离攻击框
#       2. sweep        —— 范围扫击：触发距离更宽，AOE 攻击
#   - 各自冷却独立计算，AI 在合适距离 / CD 满足时优先触发
#   - 普通近战（EnemyAttackState）作为兜底
# =============================================================
from __future__ import annotations

from entities.enemy.base_enemy   import BaseEnemy
from entities.enemy.enemy_stats  import EnemyStats
from entities.enemy.types._data_loader import (
    build_stats, get_render_params, get_loot_table_for, load_enemy_data,
)
from core.event_manager import event_manager


# 技能阶段
SKILL_NONE     = "none"
SKILL_WINDUP   = "windup"
SKILL_ACTIVE   = "active"
SKILL_COOLDOWN = "cooldown"


class _SkillRunner:
    """精英技能执行体：windup → active → cooldown 三段循环。"""

    def __init__(self, name: str, cfg: dict):
        self.name        = name
        self.windup      = int(cfg.get("windup",   30))
        self.active      = int(cfg.get("active",    6))
        self.cooldown    = int(cfg.get("cooldown", 20))
        self.damage_mul  = float(cfg.get("damage_mul", 1.0))
        self.reach       = int(cfg.get("reach",       72))
        self.poise_dmg   = float(cfg.get("poise_dmg", 20.0))
        self.min_cd_sec  = float(cfg.get("min_cd_sec", 5.0))
        self.trigger_dist = float(cfg.get("trigger_dist", 0.0))   # 0 = 无额外限制

        self.phase: str = SKILL_NONE
        self.frame: int = 0
        self.hit_done:  bool  = False
        self.cd_left:   float = 0.0   # 距离下次可释放的时间（秒）

    def is_ready(self) -> bool:
        return self.phase == SKILL_NONE and self.cd_left <= 0.0

    def is_active_phase(self) -> bool:
        return self.phase != SKILL_NONE

    def start(self) -> None:
        self.phase = SKILL_WINDUP
        self.frame = 0
        self.hit_done = False

    def cancel(self) -> None:
        # 被打断也要进入冷却，避免连点
        self.phase = SKILL_NONE
        self.frame = 0
        self.cd_left = max(self.cd_left, 1.5)

    def tick(self, dt: float):
        if self.cd_left > 0:
            self.cd_left = max(0.0, self.cd_left - dt)


class Elite(BaseEnemy):
    """古代骑士 / 堕落圣骑士。"""

    CATEGORY = "elite"

    def __init__(self, x: float, y: float):
        w, h, color = get_render_params(self.CATEGORY)
        self.color = color
        self.drop_table = list(get_loot_table_for(self.CATEGORY))
        super().__init__(x, y, width=w, height=h)

        skills_cfg = load_enemy_data(self.CATEGORY).get("elite_skills", {})
        self.charge_slash = _SkillRunner("charge_slash",
                                         skills_cfg.get("charge_slash", {}))
        self.sweep        = _SkillRunner("sweep",
                                         skills_cfg.get("sweep", {}))
        self._active_skill: _SkillRunner | None = None

    def _build_stats(self) -> EnemyStats:
        return build_stats(self.CATEGORY)

    # ------------------------------------------------------------------
    # 远程钩子：在 EnemyChaseState.update 中调用
    # 精英兵借此优先释放独特技能
    # ------------------------------------------------------------------

    def try_ranged_attack(self, dist: float) -> bool:
        if self.player is None or self.player.is_dead:
            self._cancel_active()
            return False

        # 已经在执行某个技能 → 推进
        if self._active_skill is not None:
            self.facing = 1 if self.player.x > self.x else -1
            self.vel_x = 0.0
            self._tick_skill(self._active_skill)
            return True

        # 决策：选择优先技能
        chosen: _SkillRunner | None = None

        # sweep 触发距离限制（trigger_dist > 0 时只在足够近才用）
        if self.sweep.is_ready():
            if (self.sweep.trigger_dist <= 0.0
                    or dist <= self.sweep.trigger_dist):
                chosen = self.sweep

        # charge_slash 优先级更高（伤害爆炸），需要在 reach 内才有意义
        if self.charge_slash.is_ready() and dist <= self.charge_slash.reach + 24:
            chosen = self.charge_slash

        if chosen is not None:
            self._active_skill = chosen
            self.facing = 1 if self.player.x > self.x else -1
            self.vel_x = 0.0
            chosen.start()
            event_manager.emit("elite_skill_start", {
                "enemy": self, "skill": chosen.name,
            })
            return True

        # 没有可用技能 → 让 Chase 继续，必要时落到普通近战 Attack
        return False

    # ------------------------------------------------------------------
    # 技能执行
    # ------------------------------------------------------------------

    def _tick_skill(self, sk: _SkillRunner) -> None:
        sk.frame += 1

        if sk.phase == SKILL_WINDUP:
            if sk.frame >= sk.windup:
                sk.phase = SKILL_ACTIVE
                sk.frame = 0

        elif sk.phase == SKILL_ACTIVE:
            if not sk.hit_done:
                self._resolve_skill_hit(sk)
                sk.hit_done = True
            if sk.frame >= sk.active:
                sk.phase = SKILL_COOLDOWN
                sk.frame = 0

        elif sk.phase == SKILL_COOLDOWN:
            if sk.frame >= sk.cooldown:
                sk.phase = SKILL_NONE
                sk.frame = 0
                sk.cd_left = sk.min_cd_sec
                self._active_skill = None

    def _resolve_skill_hit(self, sk: _SkillRunner) -> None:
        if self.player is None:
            return
        import pygame
        # 攻击框：朝前方 reach 像素，纵向覆盖整身
        w = sk.reach
        h = self.rect.height + 8
        if self.facing >= 0:
            ax = self.rect.centerx
        else:
            ax = self.rect.centerx - w
        ay = self.rect.centery - h // 2
        atk_rect = pygame.Rect(ax, ay, w, h)
        if not atk_rect.colliderect(self.player.rect):
            return
        kb_dir = 1 if self.player.x > self.x else -1
        damage = int(self.stats.atk * sk.damage_mul)
        try:
            self.player.take_damage(damage, kb_dir,
                                    attacker=self,
                                    poise_damage=sk.poise_dmg)
        except TypeError:
            try:
                self.player.take_damage(damage, kb_dir,
                                        poise_damage=sk.poise_dmg)
            except TypeError:
                self.player.take_damage(damage, kb_dir)

    def _cancel_active(self):
        if self._active_skill is not None:
            self._active_skill.cancel()
            self._active_skill = None

    # ------------------------------------------------------------------
    # update：推进技能 CD
    # ------------------------------------------------------------------

    def update(self, dt: float, collision_map):
        # 在主 update 之前推进 cd
        self.charge_slash.tick(dt)
        self.sweep.tick(dt)
        super().update(dt, collision_map)

    # ------------------------------------------------------------------
    # 受击：技能 windup 阶段被打断
    # ------------------------------------------------------------------

    def take_damage(self, amount: int, knockback_dir: int = 0,
                    poise_damage: float = 10.0):
        # 蓄力期间被破韧才取消（精英兵抗打断很强，普通命中不被打断）
        if (self._active_skill is not None
                and self._active_skill.phase == SKILL_WINDUP
                and self.stats.poise - poise_damage <= 0):
            self._cancel_active()
            event_manager.emit("elite_skill_interrupted", {"enemy": self})
        super().take_damage(amount, knockback_dir, poise_damage)

    # ------------------------------------------------------------------
    # 渲染：技能蓄力时显示扇形警告框 + 头顶进度条
    # ------------------------------------------------------------------

    def render(self, surface, cam_offset):
        super().render(surface, cam_offset)
        if self._active_skill is None:
            return
        sk = self._active_skill
        if sk.phase == SKILL_WINDUP:
            self._render_skill_warning(surface, cam_offset, sk)

    def _render_skill_warning(self, surface, cam_offset, sk: _SkillRunner):
        import pygame
        ox, oy = cam_offset
        ratio = max(0.0, min(1.0, sk.frame / max(1, sk.windup)))

        # 攻击预警范围（半透明红色矩形）
        w = sk.reach
        h = self.rect.height + 8
        if self.facing >= 0:
            ax = self.rect.centerx
        else:
            ax = self.rect.centerx - w
        ay = self.rect.centery - h // 2
        warn = pygame.Rect(ax - ox, ay - oy, w, h)

        overlay = pygame.Surface((warn.width, warn.height), pygame.SRCALPHA)
        # 颜色随 windup 进度由黄→红
        r = 255
        g = int(220 * (1 - ratio))
        overlay.fill((r, g, 60, 70))
        surface.blit(overlay, warn.topleft)
        pygame.draw.rect(surface, (255, 80, 80), warn, 2)

        # 头顶进度条（金色）
        bar_w = 50
        bar_h = 5
        bx = self.rect.centerx - bar_w // 2 - ox
        by = self.rect.top - 26 - oy
        pygame.draw.rect(surface, (60, 30, 30), (bx, by, bar_w, bar_h))
        filled = int(bar_w * ratio)
        if filled > 0:
            pygame.draw.rect(surface, (255, 200, 60),
                             (bx, by, filled, bar_h))
        pygame.draw.rect(surface, (255, 255, 200),
                         (bx, by, bar_w, bar_h), 1)
