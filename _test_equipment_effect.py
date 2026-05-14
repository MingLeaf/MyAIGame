# =============================================================
# _test_equipment_effect.py —— 装备效果端到端验证（第 7 阶段补丁）
#
# 验收点：
#   1. 不戴护甲 vs 戴护甲 → 受到的物理伤害必须明显减少
#   2. 不戴武器 vs 戴 sword_iron → 对敌人造成的伤害必须明显增加
#   3. 装备 4 件骑士套 (def_bonus +10%) → 物理减伤再叠一层
#   4. 装备 4 件法师套 (magic_dmg +15%) → 法术伤害更高
#   5. 戴魔法长袍 (magic_res +25) → 受到法术伤害减少
#   6. 旧 Player.take_damage(amount, kb_dir) 接口仍兼容
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1280, 720))


from entities.player.player import Player
from items.item_database  import item_db
from combat.hit_resolver  import HitResolver
from combat.floating_text import FloatingTextManager
from entities.enemy.types import Infantry, HeavyArmor, Mage


def _new_player():
    """构造一个全新的 Player（不含任何装备 / 物品）。"""
    p = Player(0.0, 0.0)
    return p


def _equip(p, slot, item_id):
    item = item_db.create(item_id)
    assert item is not None, f"找不到 {item_id}"
    p.equipment.equip(slot, item)


def _strip_armor(p):
    for slot in ("head", "chest", "hands", "legs"):
        p.equipment.unequip(slot)


# =====================================================================
print("=" * 60)
print("[1] 受击：不戴 vs 戴游侠四件套")
print("=" * 60)

# 原始伤害 50（直接调用 take_damage，不经过 HitResolver 公式，
# 因为我们要测的是 Player 自己受伤时的护甲减免逻辑）

p_naked = _new_player()
hp_before = p_naked.stats.hp
p_naked.take_damage(50, knockback_dir=0, element="physical")
naked_loss = hp_before - p_naked.stats.hp
print(f"  裸体玩家受 50 伤害 → 实扣 {naked_loss} HP")
print(f"    armor_defense = {p_naked.stats.armor_defense}, "
      f"def_bonus_pct = {p_naked.stats.def_bonus_pct}")
assert naked_loss == 50, f"裸体应直扣 50，实扣 {naked_loss}"

p_armored = _new_player()
for slot, iid in [("head", "ranger_hood"), ("chest", "ranger_vest"),
                  ("hands", "ranger_gloves"), ("legs", "ranger_boots")]:
    _equip(p_armored, slot, iid)
hp_before = p_armored.stats.hp
p_armored.take_damage(50, knockback_dir=0, element="physical")
armored_loss = hp_before - p_armored.stats.hp
print(f"  戴游侠四件套玩家受 50 伤害 → 实扣 {armored_loss} HP")
print(f"    armor_defense = {p_armored.stats.armor_defense}, "
      f"active_sets = {p_armored.set_bonus.active_set_ids()}")
assert armored_loss < naked_loss, \
    f"戴甲后应少扣血，但 {armored_loss} >= {naked_loss}"

reduction = naked_loss - armored_loss
print(f"  → 减伤 {reduction} HP（{reduction*100/naked_loss:.0f}%）✔")


# =====================================================================
print("\n" + "=" * 60)
print("[2] 受击：不戴 vs 戴骑士四件套（含 def_bonus +10% 套装）")
print("=" * 60)

p_knight = _new_player()
for slot, iid in [("head", "knight_helm"), ("chest", "knight_chest"),
                  ("hands", "knight_hands"), ("legs", "knight_legs")]:
    _equip(p_knight, slot, iid)
hp_before = p_knight.stats.hp
p_knight.take_damage(50, knockback_dir=0, element="physical")
knight_loss = hp_before - p_knight.stats.hp
print(f"  戴骑士四件套受 50 伤害 → 实扣 {knight_loss} HP")
print(f"    armor_defense = {p_knight.stats.armor_defense}, "
      f"def_bonus_pct = {p_knight.stats.def_bonus_pct}, "
      f"active_sets = {p_knight.set_bonus.active_set_ids()}")
assert "knight" in p_knight.set_bonus.active_set_ids()
assert p_knight.stats.def_bonus_pct == 0.10, \
    f"骑士套装应有 def_bonus_pct=0.10，实际 {p_knight.stats.def_bonus_pct}"
assert knight_loss < armored_loss, \
    f"骑士甲应比游侠甲减伤更多 ({knight_loss} < {armored_loss})"
print(f"  → 比游侠甲再少扣 {armored_loss - knight_loss} HP ✔")

# 单卸 1 件骑士甲：套装解除，def_bonus_pct 应回滚到 0
p_knight.equipment.unequip("head")
print(f"  卸下 1 件后 def_bonus_pct = {p_knight.stats.def_bonus_pct}, "
      f"active_sets = {p_knight.set_bonus.active_set_ids()}")
assert p_knight.stats.def_bonus_pct == 0.0, "解除套装应回滚 def_bonus_pct"
print(f"  套装效果回滚 ✔")


# =====================================================================
print("\n" + "=" * 60)
print("[3] 攻击：不戴武器 vs 戴 sword_iron (base_atk=25)")
print("=" * 60)

p1 = _new_player()
print(f"  默认 weapon = {p1.weapon.__class__.__name__}, "
      f"stats.atk = {p1.stats.atk}, weapon_item_atk = {p1.stats.weapon_item_atk}")
default_atk = p1.stats.atk
default_weapon_dmg = p1.weapon.get_light_attack(0).damage
print(f"  默认武器轻击 base damage = {default_weapon_dmg}")

# 装备 sword_iron
p2 = _new_player()
_equip(p2, "weapon", "sword_iron")
print(f"  装备 sword_iron 后 weapon = {p2.weapon.__class__.__name__}, "
      f"stats.atk = {p2.stats.atk}, weapon_item_atk = {p2.stats.weapon_item_atk}")
assert p2.stats.weapon_item_atk == 25, "sword_iron base_atk 应为 25"
assert p2.stats.atk > default_atk, \
    f"装备后 stats.atk 应增加: {p2.stats.atk} vs {default_atk}"
print(f"  → stats.atk 提升 {p2.stats.atk - default_atk} 点 ✔")

# 实际打一个 infantry，对比伤害
ftm = FloatingTextManager()
hit_resolver = HitResolver(ftm)

def simulate_one_hit(player, enemy):
    """用 weapon 的 light attack 数据生成一个 hitbox 模拟一次命中。"""
    from entities.player.attack_hitbox import AttackHitbox
    data = player.weapon.get_light_attack(0)
    # 把 hitbox 直接放在敌人位置上，确保命中
    hb = AttackHitbox(
        owner_rect    = enemy.rect.copy(),
        facing        = 1,
        offset_x      = 0,
        offset_y      = 0,
        width         = enemy.rect.width,
        height        = enemy.rect.height,
        damage        = data.damage,
        active_frames = 1,
        element       = data.element,
        poise_damage  = data.poise_damage,
        bleed_stack   = data.bleed_stack,
        source        = player,
    )
    player.active_hitboxes = [hb]
    enemy_hp_before = enemy.stats.hp
    hit_resolver.update(player, [enemy])
    return enemy_hp_before - enemy.stats.hp

# 给 p1 / p2 做 facing 朝右
for p in (p1, p2):
    p.facing = 1
    p.rect = pygame.Rect(0, 0, 24, 48)

inf1 = Infantry(60, 0); inf1.rect = pygame.Rect(50, 0, 24, 48); inf1.facing = -1
inf2 = Infantry(60, 0); inf2.rect = pygame.Rect(50, 0, 24, 48); inf2.facing = -1

dmg_naked   = simulate_one_hit(p1, inf1)
dmg_sworded = simulate_one_hit(p2, inf2)
print(f"  默认武器 1 击 infantry → 伤害 {dmg_naked}")
print(f"  铁剑武器 1 击 infantry → 伤害 {dmg_sworded}")
assert dmg_sworded > dmg_naked, \
    f"装备 sword_iron 应造成更高伤害 ({dmg_sworded} vs {dmg_naked})"
print(f"  → 多造成 {dmg_sworded - dmg_naked} 伤害 ✔")


# =====================================================================
print("\n" + "=" * 60)
print("[4] 法师套 magic_dmg +15% & 魔法长袍 magic_res +25")
print("=" * 60)

p_mage = _new_player()
for slot, iid in [("head", "mage_hat"), ("chest", "mage_robe"),
                  ("hands", "mage_gloves"), ("legs", "mage_trousers")]:
    _equip(p_mage, slot, iid)
print(f"  active_sets = {p_mage.set_bonus.active_set_ids()}")
print(f"  magic_bonus_pct = {p_mage.stats.magic_bonus_pct}, "
      f"magic_res_bonus = {p_mage.stats.magic_res_bonus}")
assert "mage" in p_mage.set_bonus.active_set_ids()
assert p_mage.stats.magic_bonus_pct == 0.15

# 受到 magic 伤害（30）：物理护甲不抵，但魔法抗性减伤
p_mage_hp_before = p_mage.stats.hp
p_mage.take_damage(30, knockback_dir=0, element="fire")
mage_loss = p_mage_hp_before - p_mage.stats.hp
print(f"  法师套受 30 火伤 → 实扣 {mage_loss} HP "
      f"(magic_res_bonus={p_mage.stats.magic_res_bonus})")
# magic_res = 65, after_armor = 30 - 65*0.5 = 30 - 32.5 = -2.5 → max(1) → 1
assert mage_loss < 30, "法师套应该对法术显著减伤"
print(f"  → 比裸体（30 全扣）减伤 {30 - mage_loss} HP ✔")

# 同样 30 物理伤害，法师套护甲很低 (2+5+1+3=11) → 减伤少
p_mage2 = _new_player()
for slot, iid in [("head", "mage_hat"), ("chest", "mage_robe"),
                  ("hands", "mage_gloves"), ("legs", "mage_trousers")]:
    _equip(p_mage2, slot, iid)
p_mage2_hp_before = p_mage2.stats.hp
p_mage2.take_damage(30, knockback_dir=0, element="physical")
phys_loss = p_mage2_hp_before - p_mage2.stats.hp
print(f"  法师套受 30 物伤 → 实扣 {phys_loss} HP "
      f"(armor_defense={p_mage2.stats.armor_defense})")
assert phys_loss > mage_loss, \
    f"法师套对物理减伤应弱于对法术 ({phys_loss} > {mage_loss})"
print(f"  → 法师套抗法 ({mage_loss}) <<< 抗物 ({phys_loss}) ✔")


# =====================================================================
print("\n" + "=" * 60)
print("[5] 旧接口兼容：take_damage(amount, kb_dir) 三参数版")
print("=" * 60)

p_old = _new_player()
hp_before = p_old.stats.hp
# 模拟旧调用风格（不传 element / poise_damage）
p_old.take_damage(20, 1)
print(f"  旧三参数调用 → 扣 {hp_before - p_old.stats.hp} HP ✔")
assert hp_before - p_old.stats.hp == 20  # 裸体 → 全扣


# =====================================================================
print("\n" + "=" * 60)
print("[6] 完整流程：grant_starting_kit 后实际游戏中受 mage MagicBall 伤害")
print("=" * 60)

p_full = _new_player()
p_full.grant_starting_kit()
print(f"  starting_kit weapon = {p_full.weapon.__class__.__name__} "
      f"stats.atk = {p_full.stats.atk}")
print(f"  armor_defense = {p_full.stats.armor_defense}, "
      f"magic_res_bonus = {p_full.stats.magic_res_bonus}")
print(f"  active_sets = {p_full.set_bonus.active_set_ids()}")

from physics.projectile import MagicBall

# 直接模拟 MagicBall 命中
ball = MagicBall(
    x=0, y=0, vx=-100, vy=0,
    damage=40, owner=None,
    element="fire", lifetime=1.0,
)
hp_before = p_full.stats.hp
ball.on_hit(p_full)
loss_with_ranger = hp_before - p_full.stats.hp
print(f"  game_started (游侠套) 受 40 火伤 → 实扣 {loss_with_ranger} HP")
print(f"    （游侠套是物理护甲，magic_res=0，所以对火伤无减免）")
assert loss_with_ranger == 40

# 切换到法师套：法术减伤
p_caster = _new_player()
for slot, iid in [("head", "mage_hat"), ("chest", "mage_robe"),
                  ("hands", "mage_gloves"), ("legs", "mage_trousers")]:
    _equip(p_caster, slot, iid)
ball2 = MagicBall(x=0, y=0, vx=-100, vy=0, damage=40, owner=None,
                  element="fire", lifetime=1.0)
hp_before = p_caster.stats.hp
ball2.on_hit(p_caster)
loss_with_mage = hp_before - p_caster.stats.hp
print(f"  法师四件套受 40 火伤 → 实扣 {loss_with_mage} HP "
      f"(magic_res_bonus={p_caster.stats.magic_res_bonus})")
assert loss_with_mage < loss_with_ranger
print(f"  → 法师套对法术减伤 {loss_with_ranger - loss_with_mage} HP，"
      f"远胜物理护甲 ✔")

# 物理 MagicBall 测试：游侠套 vs 法师套对物理伤害
from physics.projectile import Arrow
arr1 = Arrow(x=0, y=0, vx=-100, vy=0, damage=40, owner=None,
             element="physical", lifetime=1.0)
p_full2 = _new_player()
p_full2.grant_starting_kit()
hp_before = p_full2.stats.hp
arr1.on_hit(p_full2)
loss_ranger_phys = hp_before - p_full2.stats.hp

arr2 = Arrow(x=0, y=0, vx=-100, vy=0, damage=40, owner=None,
             element="physical", lifetime=1.0)
hp_before = p_caster.stats.hp
arr2.on_hit(p_caster)
loss_mage_phys = hp_before - p_caster.stats.hp

print(f"  对比 40 物理箭：")
print(f"    游侠套 → 实扣 {loss_ranger_phys} HP "
      f"(armor_defense={p_full2.stats.armor_defense})")
print(f"    法师套 → 实扣 {loss_mage_phys} HP "
      f"(armor_defense={p_caster.stats.armor_defense})")
assert loss_ranger_phys < loss_mage_phys, \
    "游侠套物理护甲应高于法师套"
print(f"  → 游侠套抗物 ({loss_ranger_phys}) << 法师套抗物 ({loss_mage_phys}) ✔")


# =====================================================================
print("\n" + "=" * 60)
print("✅ 装备效果端到端验证全部通过！")
print("=" * 60)
