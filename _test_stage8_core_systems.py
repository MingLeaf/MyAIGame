# =============================================================
# _test_stage8_core_systems.py —— 第 8 阶段冒烟测试
#
# 测试：灵魂碎片系统 / 复活系统 / 营地系统 / 升级系统 / 强化系统 / 进度系统
# =============================================================
import os
import sys
import math

# 抑制 SDL 视频输出（无头跑测试）
os.environ["SDL_VIDEODRIVER"] = "dummy"

# ---- 0. 初始化 Pygame ----
import pygame
pygame.init()
pygame.font.init()

print("=" * 60)
print("第 8 阶段冒烟测试：游戏规则核心系统")
print("=" * 60)

# ---- 1. 基础导入测试 ----
print("\n[1] 模块导入测试...")

from systems.soul_fragment_system import SoulFragmentSystem, DeathRelic
from systems.respawn_system       import RespawnSystem
from systems.campfire_system      import CampfireSystem
from systems.progression_system   import ProgressionSystem
from systems.upgrade_system       import UpgradeSystem
from systems.quest_system         import QuestSystem

print("  ✓ 所有系统模块导入成功")

# ---- 2. 进度系统测试 ----
print("\n[2] QuestSystem 测试...")
QuestSystem.hard_reset()
assert QuestSystem.is_area_unlocked("area_graveyard"), "起始区域应已解锁"
QuestSystem.record_campfire("cf_test_01")
assert QuestSystem.is_campfire_activated("cf_test_01")
QuestSystem.record_boss_kill("duke_rotbone")
assert QuestSystem.is_boss_killed("duke_rotbone")
summary = QuestSystem.progress_summary()
assert "duke_rotbone" in summary["killed_bosses"]
print(f"  ✓ 进度摘要: {summary}")

# ---- 3. 灵魂碎片系统测试 ----
print("\n[3] SoulFragmentSystem 测试...")

# 创建 mock 玩家
class MockStats:
    hp = 100; max_hp = 100; stamina = 100.0; max_stamina = 100.0
    mana = 50; max_mana = 50; is_dead = False
    atk = 0; armor_defense = 0; weapon_item_atk = 0
    atk_bonus_pct = 0.0; def_bonus_pct = 0.0; magic_bonus_pct = 0.0; magic_res_bonus = 0
    def apply_growth(self, *a, **kw): pass
    def update(self, dt): pass

class MockGrowth:
    strength = 10; dexterity = 10; intelligence = 5; faith = 5
    vitality = 10; endurance = 10; equip_weight = 0.0; unspent_points = 0
    max_hp_bonus = 0; max_stamina_bonus = 0.0; roll_type = "normal"
    def allocate(self, attr, points=1): return True
    def get_atk_bonus(self, w=None): return 0
    def gain_points(self, n=1): self.unspent_points += n

class MockBuild:
    level = 1; exp = 0; unspent = 0
    def _level_up(self):
        self.level += 1
        self.unspent += 1

class MockPlayer:
    def __init__(self):
        self.stats = MockStats()
        self.growth = MockGrowth()
        self.build = MockBuild()
        self.soul_fragments = 0
        self.x = 100; self.y = 200
        from pygame import Rect
        self.rect = Rect(100, 200, 24, 48)
        self.weapon = None
        self.vel_x = 0.0
        self.fsm = None  # Mock 不够完整，仅测试核心逻辑

    def allocate_stat(self, attr, points=1):
        return True

class MockEnemy:
    def __init__(self, category="infantry", level=1):
        self.CATEGORY = category
        self.level = level
        from pygame import Rect
        self.rect = Rect(300, 200, 32, 48)

player = MockPlayer()
enemy = MockEnemy("infantry", 1)

# 测试灵魂碎片掉落
gained = SoulFragmentSystem.grant_for_enemy(player, enemy)
assert gained > 0, f"应获得碎片，实际 {gained}"
assert player.soul_fragments == gained
print(f"  ✓ 击杀 {enemy.CATEGORY} Lv.{enemy.level} → +{gained} 灵魂")

# 测试精英掉落更多
elite = MockEnemy("elite", 3)
before = player.soul_fragments
gained2 = SoulFragmentSystem.grant_for_enemy(player, elite)
assert gained2 > gained, f"精英掉落 ({gained2}) 应多于普通 ({gained})"
print(f"  ✓ 精英 Lv.{elite.level} → +{gained2} 灵魂（>{gained}）")

# 测试 DeathRelic 渲染对象
relic = DeathRelic(150, 200, 500)
assert relic.soul_count == 500
print(f"  ✓ DeathRelic 创建成功：{relic.soul_count} 灵魂 @ ({relic.x}, {relic.y})")

# ---- 4. 营地系统测试 ----
print("\n[4] CampfireSystem 测试...")
CampfireSystem.activate("cf_start", "area_graveyard", 224, 600)
assert CampfireSystem.is_activated("cf_start")
assert CampfireSystem.get_last_campfire() == "cf_start"
pos = CampfireSystem.get_position("cf_start")
assert pos["area_id"] == "area_graveyard"
print(f"  ✓ 营地 'cf_start' 已激活, 位置: ({pos['x']}, {pos['y']})")

targets = CampfireSystem.get_transport_targets("cf_start")
assert len(targets) == 0  # 只有一个营地，无传送目标
print(f"  ✓ 传送目标数: {len(targets)}（当前仅 1 个营地）")

# 激活第二个营地
CampfireSystem.activate("cf_mid", "area_graveyard", 1504, 450)
targets = CampfireSystem.get_transport_targets("cf_start")
assert len(targets) == 1
print(f"  ✓ 激活第 2 个营地后传送目标: {len(targets)}")

# ---- 5. 升级系统测试 ----
print("\n[5] ProgressionSystem 测试...")
# 读取等级数据
ProgressionSystem.load_data()
cost_lv2 = ProgressionSystem.get_level_cost(2)
cost_lv3 = ProgressionSystem.get_level_cost(3)
assert cost_lv2 > 0
assert cost_lv3 > cost_lv2, f"Lv3 成本 ({cost_lv3}) 应 > Lv2 ({cost_lv2})"
print(f"  ✓ Lv1→2: {cost_lv2} 灵魂, Lv2→3: {cost_lv3} 灵魂")

# 测试升级
p2 = MockPlayer()
p2.soul_fragments = 10000  # 给足够多的灵魂
# 重写 build._level_up 为绑定方法
p2.build._level_up = lambda: MockBuild._level_up(p2.build)
leveled = ProgressionSystem.spend_souls_to_level_up(p2, 5)
assert leveled > 0, f"应升级至少 1 级，实际 {leveled}"
assert p2.build.level > 1
print(f"  ✓ 消耗灵魂 → 从 Lv1 升到 Lv{p2.build.level}（实际升 {leveled} 级）")

# 测试灵魂不足
p3 = MockPlayer()
p3.soul_fragments = 10
p3.build._level_up = lambda: MockBuild._level_up(p3.build)
p3.allocate_stat = lambda attr, points=1: True
leveled2 = ProgressionSystem.spend_souls_to_level_up(p3, 3)
assert leveled2 == 0, "灵魂不足时应无法升级"
print(f"  ✓ 灵魂不足 ({p3.soul_fragments}) → 升级 {leveled2} 级")

# ---- 6. 武器强化系统测试 ----
print("\n[6] UpgradeSystem 测试...")
UpgradeSystem.load_data()

# 查询成本
souls_cost, mat_qty, _ = UpgradeSystem.get_upgrade_cost(1)
assert souls_cost > 0
assert mat_qty == 0  # +1 不需要材料
print(f"  ✓ +0→+1: {souls_cost} 灵魂, 材料: {mat_qty}")

souls_cost6, mat_qty6, _ = UpgradeSystem.get_upgrade_cost(6)
assert mat_qty6 > 0, "+6 应需要材料"
print(f"  ✓ +5→+6: {souls_cost6} 灵魂, 材料: {mat_qty6}")

# 预览
preview = UpgradeSystem.preview_upgrade(p2)
# p2 没有武器，preview 返回 error
print(f"  ✓ 预览升级: {preview}")

# ---- 7. 复活系统测试 ----
print("\n[7] RespawnSystem 测试...")
# 验证模块可导入（实际复活流程需要完整 Player + Area，在集成测试中验证）
print("  ✓ RespawnSystem 导入成功（完整流程需集成测试）")

# ---- 8. 数据文件验证 ----
print("\n[8] JSON 数据文件验证...")
from utils.json_loader import load_from_data_dir

# level_curve.json
lcfg = load_from_data_dir("balance/level_curve.json")
assert len(lcfg["levels"]) == 50
print(f"  ✓ level_curve.json: {len(lcfg['levels'])} levels, base={lcfg.get('base')}, exponent={lcfg.get('exponent')}")

# upgrade_cost.json
ucfg = load_from_data_dir("balance/upgrade_cost.json")
assert ucfg["route_branch_level"] == 5
assert len(ucfg["levels"]) == 10
assert len(ucfg["materials"]) == 4
print(f"  ✓ upgrade_cost.json: 路线分支 Lv{ucfg['route_branch_level']}, {len(ucfg['levels'])} levels, {len(ucfg['materials'])} routes")

# ---- 9. HUD 集成测试 ----
print("\n[9] HUD 灵魂碎片显示...")
from ui.hud import HUD
hud = HUD()
# 验证 HUD 可正常渲染（不会因为 soul_fragments 缺失而崩溃）
p_hud = MockPlayer()
p_hud.build = MockBuild()
p_hud.soul_fragments = 1234
p_hud.current_state = "Idle"
p_hud.stats.hp_ratio = 1.0
p_hud.stats.stamina_ratio = 1.0
p_hud.stats.mana_ratio = 0.8
surf = pygame.Surface((1280, 720))
hud.render(surf, p_hud)
print("  ✓ HUD 渲染（含灵魂碎片显示）成功 - 无崩溃")

# ---- 10. Area death_relic 字段 ----
print("\n[10] Area 集成测试...")
from map.area import Area
area = Area("area_graveyard")
assert area.death_relic is None
print("  ✓ Area.death_relic 初始为 None")

# ---- 结果 ----
print("\n" + "=" * 60)
print("  ✅ 第 8 阶段全部 10 组测试通过！")
print("=" * 60)
print("\n🎯 核心系统摘要:")
print(f"   - 灵魂碎片：敌人死亡 → 掉落碎片（按类型/等级倍率）")
print(f"   - 死亡遗物：死亡位置生成脉动光球，含全部碎片")
print(f"   - 营地复活：传送到最近营地 + 恢复 + 补满消耗品 + 敌人重置")
print(f"   - 营地系统：激活注册 + 传送网络 + 消耗品自动补满")
print(f"   - 升级系统：消耗灵魂碎片升 Lv1~50，每级 1 属性点")
print(f"   - 强化系统：+1~+5 仅灵魂碎片，+6~+10 加材料（4 路线）")
print(f"   - 进度系统：Boss 击杀 + 区域解锁 + 营地追踪")
print(f"   - HUD 显示：右下角显示灵魂碎片数和等级")
print(f"   - 数据驱动：level_curve.json + upgrade_cost.json")

pygame.quit()
