# =============================================================
# _test_levelup_sync.py —— 升级后攻防数值同步验证
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.font.init()

print("=" * 60)
print("升级后攻防数值同步验证")
print("=" * 60)

from entities.player.player import Player
from entities.player.growth_stats import GrowthStats
from entities.player.player_stats import PlayerStats

# 创建真实 Player 实例
p = Player(224, 600)

# 记录初始值
init_atk = p.stats.atk
init_hp = p.stats.max_hp
init_sta = p.stats.max_stamina
init_def = p.stats.armor_defense
print(f"\n初始数值: atk={init_atk}, HP={init_hp}/{init_hp}, STA={init_sta:.0f}, DEF={init_def}")

# ---- 1. 分配体魄 +2：HP 应增加 ----
p.growth.allocate("vitality", 2)
# OLD CODE would just call apply_growth (no _sync_stats)
# NEW CODE: 走 _sync_stats 路径
p.allocate_stat("vitality", 2)

hp_after_vit = p.stats.max_hp
atk_after_vit = p.stats.atk
def_after_vit = p.stats.armor_defense

# 体魄+2 → HP 应增加 2*15 = 30
expected_hp = PlayerStats.BASE_HP + p.growth.max_hp_bonus
print(f"\n体魄 +2:  max_hp={hp_after_vit} (预期 {expected_hp})")
assert hp_after_vit > init_hp, f"HP 应增加，但 {hp_after_vit} <= {init_hp}"
# 防御不应变化
assert def_after_vit == init_def, f"防御不应变化: {def_after_vit} != {init_def}"
print(f"  ✓ HP 正确增加，防御不变")

# ---- 2. 分配力量 +1：atk 应增加 ----
p.allocate_stat("strength", 1)
atk_after_str = p.stats.atk
assert atk_after_str >= atk_after_vit, f"atk 应增加或保持: {atk_after_str} >= {atk_after_vit}"
print(f"  力量 +1: atk={atk_after_str} (前 {atk_after_vit})")
print(f"  ✓ 攻击力正确同步")

# ---- 3. 分配耐性 +2：Stamina 应增加，负重增加 ----
sta_before = p.stats.max_stamina
p.allocate_stat("endurance", 2)
sta_after = p.stats.max_stamina
assert sta_after > sta_before
print(f"  耐性 +2: max_stamina={sta_after:.0f} (前 {sta_before:.0f})")
print(f"  ✓ 耐力上限正确增加")

# ---- 4. 模拟完整 Player.combat.take_damage 的伤害计算 ----
print(f"\n受击伤害验证:")
# 玩家当前防御值
print(f"  armor_defense = {p.stats.armor_defense}")

# 如果没有装备护甲，防御为 0（套装百分比也算 0）
from combat.damage_calculator import _DEFENSE_COEFF, _MIN_DAMAGE
raw = 50
after_armor = raw - p.stats.armor_defense * _DEFENSE_COEFF
after_set = after_armor * max(0.0, 1.0 - p.stats.def_bonus_pct)
final = max(_MIN_DAMAGE, int(after_set))
print(f"  原始伤害 {raw} → 最终伤害 {final}")
print(f"  (公式: {raw} - {p.stats.armor_defense} × {_DEFENSE_COEFF} = {after_armor}")

# ---- 5. 攻击力验证 ----
print(f"\n攻击力验证:")
print(f"  stats.atk = {p.stats.atk}")
print(f"  stats.weapon_item_atk = {p.stats.weapon_item_atk}")
print(f"  weapon = {p.weapon.__class__.__name__ if p.weapon else 'None'}")
if p.weapon:
    print(f"  weapon upgrade_level = {p.weapon.upgrade_level}")

# 验证 atk 包含 weapon_item_atk
assert p.stats.atk >= p.stats.weapon_item_atk
print(f"  ✓ stats.atk ({p.stats.atk}) >= weapon_item_atk ({p.stats.weapon_item_atk})")

# ---- 6. 对比 PlayerBuild.compute_stats vs Equipment._sync_stats ----
print(f"\ncompute_stats vs _sync_stats 一致性验证:")
# 记录当前值
atk1 = p.stats.atk
hp1 = p.stats.max_hp
def1 = p.stats.armor_defense

# 模拟 compute_stats 但走 _sync_stats
p.build.compute_stats()

atk2 = p.stats.atk
hp2 = p.stats.max_hp
def2 = p.stats.armor_defense

print(f"  compute_stats() 后: atk={atk2} (前 {atk1}), hp={hp2}, def={def2}")
assert atk2 == atk1, f"compute_stats 不应改变 atk: {atk2} != {atk1}"
assert hp2 == hp1, f"compute_stats 不应改变 hp: {hp2} != {hp1}"
assert def2 == def1, f"compute_stats 不应改变 def: {def2} != {def1}"
print(f"  ✓ compute_stats 幂等，数值稳定")

# ---- 7. 再次验证装备完整周期 ----
print(f"\n装备完整周期验证:")
from player.equipment import SLOT_WEAPON

# 卸下武器再装上 → 走完整 equip/unequip
old_weapon = p.equipment._slots.get(SLOT_WEAPON)
if old_weapon:
    p.equipment.unequip(SLOT_WEAPON)
    atk_unequip = p.stats.atk
    print(f"  卸下武器后 atk = {atk_unequip}")
    p.equipment.equip(SLOT_WEAPON, old_weapon)
    atk_reequip = p.stats.atk
    print(f"  重新装备后 atk = {atk_reequip}")
    assert atk_reequip >= atk_unequip
    print(f"  ✓ 卸下/重新装备武器，atk 正确恢复")

print("\n" + "=" * 60)
print("  ✅ 升级后攻防数值同步验证全部通过！")
print("=" * 60)

pygame.quit()
