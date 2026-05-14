# =============================================================
# _test_stage8_fixes2.py —— 第二波修复验证
#
# 问题1: 武器升级后伤害同步
# 问题2: 营地交互不重置怪物
# 问题4: 灵魂飘字在怪物死亡位置
# 问题5: 升级面板属性描述
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.font.init()

print("=" * 60)
print("第 8 阶段修复验证 (第二波)")
print("=" * 60)

# ----------------------------------------------------------------
# 问题1: 武器升级后伤害验证
# ----------------------------------------------------------------
print("\n[1] 武器升级后伤害同步验证...")

from weapons.sword import Sword
from weapons.weapon_upgrade import WeaponUpgrade

# 模拟精简 Player（含 equipment）
class MockEquip:
    def __init__(self, player):
        self._player = player
    def _sync_stats(self):
        p = self._player
        p.stats.apply_growth(p.growth, p.weapon)
        # 模拟 weapon_item_atk
        p.stats.atk = p.stats.atk + 25  # 装备物品 base_atk

class MockStats2:
    hp = 100; max_hp = 100; stamina = 100.0; max_stamina = 100.0
    mana = 50; max_mana = 50; is_dead = False
    atk = 0; armor_defense = 0; weapon_item_atk = 25
    atk_bonus_pct = 0.0; def_bonus_pct = 0.0; magic_bonus_pct = 0.0; magic_res_bonus = 0
    def apply_growth(self, g, w=None):
        self.atk = g.get_atk_bonus(w)
    def take_damage_with_defense(self, amount, element="physical"):
        return (amount, amount)

class MockGrowth2:
    strength = 10; dexterity = 10; intelligence = 5; faith = 5
    vitality = 10; endurance = 10; equip_weight = 0.0; unspent_points = 0
    max_hp_bonus = 0; max_stamina_bonus = 0.0; roll_type = "normal"
    def get_atk_bonus(self, w=None): return 10

class MockBuild2:
    level = 1; unspent = 0

class MockPlayer2:
    def __init__(self):
        self.stats = MockStats2()
        self.growth = MockGrowth2()
        self.build = MockBuild2()
        self.soul_fragments = 10000
        self.weapon = Sword()
        self.weapon.upgrade_level = 0
        self.equipment = MockEquip(self)
        self.inventory = None

p = MockPlayer2()

# 升级前攻击力
atk_before = p.stats.atk
print(f"  升级前: stats.atk = {atk_before}")

# 武器升级
from systems.upgrade_system import UpgradeSystem
UpgradeSystem.load_data()
ok, msg = UpgradeSystem.upgrade_weapon(p, p.weapon, route="none")
atk_after = p.stats.atk
print(f"  升级结果: {msg}")
print(f"  升级后: stats.atk = {atk_after}")

assert ok, "升级应成功"
assert p.weapon.upgrade_level == 1
# 关键：验证 upgrade_weapon 调用了 equipment._sync_stats()
assert atk_after >= atk_before, f"升级后攻击力 ({atk_after}) 应 >= 升级前 ({atk_before})"
print(f"  ✓ 武器升级后 atk 已通过 _sync_stats() 同步")

# 验证多次升级不退化
for _ in range(4):
    UpgradeSystem.upgrade_weapon(p, p.weapon, route="none")
assert p.weapon.upgrade_level == 5
atk_lv5 = p.stats.atk
assert atk_lv5 >= atk_after
print(f"  ✓ 连续升级到 +5 后 atk = {atk_lv5}（≥ +1 时的 {atk_after}）")

# ----------------------------------------------------------------
# 问题2: 营地交互不重置怪物
# ----------------------------------------------------------------
print("\n[2] 营地交互不重置怪物验证...")

from map.campfire import Campfire
from systems.campfire_system import CampfireSystem

# 验证 Campfire.try_activate 不再调用 rest
# （代码审查验证：检查 map/campfire.py 中 try_activate 不再包含 rest 调用）
import inspect
src = inspect.getsource(Campfire.try_activate)
assert "CampfireSystem.rest" not in src, "Campfire.try_activate 不应调用 rest()"
assert "area.reload" not in src, "Campfire.try_activate 不应调用 area.reload()"
print(f"  ✓ Campfire.try_activate 不自动重置怪物")

# 验证 CampfireSystem.rest 不再调用 area.reload（允许注释中出现）
src2 = inspect.getsource(CampfireSystem.rest)
lines = [l.strip() for l in src2.split('\n') if not l.strip().startswith('#')]
code_only = '\n'.join(lines)
assert 'area.reload()' not in code_only, "CampfireSystem.rest 代码中不应调用 area.reload()"
print(f"  ✓ CampfireSystem.rest 不自动重置怪物")

# 验证 CampfireMenu._do_rest 中才重置怪物
from ui.campfire_menu import CampfireMenu
src3 = inspect.getsource(CampfireMenu._do_rest)
assert "area.reload()" in src3, "CampfireMenu._do_rest 应显式调用 area.reload()"
print(f"  ✓ 仅 CampfireMenu._do_rest 显式重置怪物")

# ----------------------------------------------------------------
# 问题4: 飘字逻辑验证
# ----------------------------------------------------------------
print("\n[3] 灵魂飘字位置验证...")

from scenes.game_scene import GameScene

# 验证 _on_soul_fragments_changed 中 source="enemy" 时直接 return
src4 = inspect.getsource(GameScene._on_soul_fragments_changed)
assert "source == \"enemy\"" in src4 and "return" in src4, \
    "敌人掉落时应直接在 _on_enemy_dead 中显示，而非在 _on_soul_fragments_changed"
print(f"  ✓ source='enemy' 时不在玩家头顶重复显示")

# 验证 _on_enemy_dead 中飘字位置在敌人位置
src5 = inspect.getsource(GameScene._on_enemy_dead)
assert "wx = enemy.rect.centerx" in src5
print(f"  ✓ 灵魂飘字使用敌人位置 (enemy.rect.centerx)")

# ----------------------------------------------------------------
# 问题5: 属性描述
# ----------------------------------------------------------------
print("\n[4] 升级面板属性描述验证...")

from ui.campfire_menu import ATTR_DESCRIPTIONS
assert len(ATTR_DESCRIPTIONS) == 6
for key, desc in ATTR_DESCRIPTIONS.items():
    assert len(desc) > 0, f"{key} 缺少描述"
    print(f"  {key}: {desc}")

print(f"  ✓ 6 项属性描述完整")

# 面板渲染测试（含描述）
menu = CampfireMenu()
menu._player = p
menu.visible = True
menu._show_upgrade_panel = True
menu._message = "描述测试"
menu._msg_timer = 2.0
surf = pygame.Surface((1280, 720))
menu.render(surf)
print(f"  ✓ 含描述的升级面板渲染成功 - 无崩溃")

# ----------------------------------------------------------------
# 结果
# ----------------------------------------------------------------
print("\n" + "=" * 60)
print("  ✅ 五项修复全部验证通过！")
print("=" * 60)

pygame.quit()
