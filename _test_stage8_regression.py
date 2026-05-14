# =============================================================
# _test_stage8_regression.py —— 第 8 阶段回归验证
#
# 确认已有模块仍然正常导入、第 8 阶段新模块不破坏原有代码。
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.font.init()

print("=" * 60)
print("第 8 阶段回归验证")
print("=" * 60)

errors = []

def check(desc, fn):
    try:
        fn()
        print(f"  ✓ {desc}")
    except Exception as e:
        print(f"  ✗ {desc}: {e}")
        errors.append(desc)

# ---- core ----
check("core.game",     lambda: __import__("core.game"))
check("core.event_manager", lambda: __import__("core.event_manager"))
check("core.input_handler", lambda: __import__("core.input_handler"))

# ---- combat ----
check("combat.damage_calculator", lambda: __import__("combat.damage_calculator"))
check("combat.status_effects",    lambda: __import__("combat.status_effects"))
check("combat.drop_system",       lambda: __import__("combat.drop_system"))
check("combat.parry_system",      lambda: __import__("combat.parry_system"))

# ---- weapons ----
check("weapons.base_weapon",  lambda: __import__("weapons.base_weapon"))
check("weapons.sword",        lambda: __import__("weapons.sword"))
check("weapons.weapon_upgrade", lambda: __import__("weapons.weapon_upgrade"))

# ---- items ----
check("items.item_database", lambda: __import__("items.item_database"))
check("items.item_manager",  lambda: __import__("items.item_manager"))

# ---- entities ----
check("entities.base_entity",     lambda: __import__("entities.base_entity"))
check("entities.player.player",   lambda: __import__("entities.player.player"))
check("entities.enemy.base_enemy",lambda: __import__("entities.enemy.base_enemy"))

# ---- map ----
check("map.area",      lambda: __import__("map.area"))
check("map.world_map", lambda: __import__("map.world_map"))
check("map.campfire",  lambda: __import__("map.campfire"))

# ---- scenes ----
check("scenes.game_scene", lambda: __import__("scenes.game_scene"))

# ---- systems (new) ----
check("systems (all)", lambda: (
    __import__("systems.soul_fragment_system"),
    __import__("systems.respawn_system"),
    __import__("systems.campfire_system"),
    __import__("systems.progression_system"),
    __import__("systems.upgrade_system"),
    __import__("systems.quest_system"),
))

# ---- 关键类实例化 ----
from entities.player.player import Player
p = Player(100, 600)
check("Player.__init__", lambda: None)
assert hasattr(p, "soul_fragments"), "Player 缺少 soul_fragments 字段"
assert p.soul_fragments == 0
print(f"  ✓ Player.soul_fragments = {p.soul_fragments}")

# ---- 武器创建 ----
from weapons import sword
sw = sword.Sword()
check("Sword 创建", lambda: None)
assert hasattr(sw, "upgrade_level")
print(f"  ✓ Sword upgrade_level = {sw.upgrade_level}")

# ---- 物品数据库加载 ----
from items.item_database import item_db
check("item_db 加载", lambda: None)
print(f"  ✓ item_db 已加载 {len(item_db._db)} 个物品")

print("\n" + "=" * 60)
if errors:
    print(f"  ❌ {len(errors)} 项失败:")
    for e in errors:
        print(f"     - {e}")
else:
    print("  ✅ 所有回归测试通过！第 8 阶段零破坏。")
print("=" * 60)

pygame.quit()
