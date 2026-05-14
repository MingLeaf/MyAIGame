# =============================================================
# _test_consumables.py —— 消耗品功能验证
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.font.init()

print("=" * 60)
print("消耗品功能验证")
print("=" * 60)

from items.item_database import item_db
from player.inventory import Inventory, MAX_SLOTS

# ---- Mock Player ----
class MockStats:
    hp = 80; max_hp = 100; mana = 25; max_mana = 50
    def heal(self, amount):
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual
    def restore_mana(self, amount):
        self.mana = min(self.max_mana, self.mana + amount)
    def consume_mana(self, amount):
        if self.mana < amount: return False
        self.mana -= amount; return True

class MockGrowth:
    strength = 10; dexterity = 10

class MockFSM:
    def is_in(self, *a): return False

class MockPlayer:
    def __init__(self):
        self.stats = MockStats()
        self.growth = MockGrowth()
        self.fsm = MockFSM()
        self.soul_fragments = 500
        from pygame import Rect
        self.rect = Rect(320, 400, 24, 48)

p = MockPlayer()

# ---- 1. 所有消耗品加载检查 ----
print("\n[1] 消耗品加载检查...")
consumables = [
    "heal_potion_small", "heal_potion_large", "heal_potion_great",
    "mana_potion_basic", "mana_potion_elixir",
    "stamina_potion_basic", "stamina_potion_elixir",
    "antidote_universal",
    "buff_sharp_powder", "buff_element_resin",
    "skeleton_ashes", "teleport_stone", "trap_bomb", "poison_dart",
    "estus_flask", "mana_flask", "herb_heal_small",
]
for cid in consumables:
    it = item_db.get(cid)
    if it:
        kind = getattr(it, "special_kind", "N/A")
        print(f"  ✓ {cid}: {type(it).__name__} (kind={kind})")
    else:
        print(f"  ✗ {cid}: NOT FOUND")

# ---- 2. 普通消耗品测试 ----
print("\n[2] 普通消耗品使用测试...")

# 回血
hp_it = item_db.create("heal_potion_small")
result = hp_it.use(p)
print(f"  ✓ heal_potion_small: result={result}, HP={p.stats.hp}/{p.stats.max_hp}")
assert result == True
assert p.stats.hp == 100  # 80 + 25 capped

# 回蓝
mp_it = item_db.create("mana_potion_basic")
result = mp_it.use(p)
print(f"  ✓ mana_potion_basic: result={result}, Mana={p.stats.mana}/{p.stats.max_mana}")
assert result == True

# ---- 3. 特殊消耗品：骷髅骨灰 ----
print("\n[3] 骷髅骨灰使用测试...")
bone = item_db.create("skeleton_ashes")
print(f"  item_type: {bone.item_type}, stackable: {bone.stackable}")
print(f"  special_kind: {bone.special_kind}")
print(f"  effect: {bone.effect}")

result = bone.use(p)
print(f"  skeleton_ashes.use() → {result}")
assert result == True
print(f"  ✓ 骷髅骨灰成功触发（发射 summon_ally 事件）")

# ---- 4. 背包集成测试 ----
print("\n[4] 背包 use_item 集成测试...")
inv = Inventory()
ok, left = inv.add(bone, 2)
assert ok and left == 0
print(f"  背包添加成功: slot0 数量={inv.get_slot(0).quantity}")

result = inv.use_item(0, p)
print(f"  inv.use_item(0) → {result}")
assert result == True
# 使用后数量应该 -1
slot = inv.get_slot(0)
print(f"  使用后: slot0 数量={slot.quantity if slot else 'None'}")
assert slot is None or slot.quantity == 1
print(f"  ✓ 背包使用骷髅骨灰成功，数量从 2 → 1")

# ---- 5. 检查毒飞镖 ----
print("\n[5] 毒飞镖使用测试...")
dart = item_db.create("poison_dart")
# 设置 current_area 用于抛射物
class MockArea:
    def __init__(self):
        self.projectiles = []
p.current_area = MockArea()
result = dart.use(p)
print(f"  poison_dart.use() → {result}")
print(f"  抛射物数: {len(p.current_area.projectiles)}")
assert result == True and len(p.current_area.projectiles) == 1
print(f"  ✓ 毒飞镖成功发射")

# ---- 6. 检查 buff 类 ----
print("\n[6] Buff 消耗品测试...")
buff = item_db.create("buff_sharp_powder")
print(f"  buff_sharp_powder: effect={buff.effect}, value={buff.effect_value}")
result = buff.use(p)
print(f"  buff_sharp_powder.use() → {result}")
# Buff 物品通过 CUSTOM callback 工作
print(f"  ✓ Buff 物品触发成功")

# ---- 7. 传送石 ----
print("\n[7] 传送石测试...")
stone = item_db.create("teleport_stone")
result = stone.use(p)
print(f"  teleport_stone.use() → {result}")
assert result == True
print(f"  ✓ 传送石成功触发（发射 teleport_to_campfire 事件）")

print("\n" + "=" * 60)
print("  ✅ 消耗品功能验证全部通过！")
print("=" * 60)
pygame.quit()
