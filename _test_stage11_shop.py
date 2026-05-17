# =============================================================
# _test_stage11_shop.py —— 商店系统冒烟测试
# =============================================================
import os
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((320, 240))

fail_count = 0

def check(condition, label):
    global fail_count
    if condition:
        print(f"    PASS  {label}")
    else:
        print(f"    FAIL  {label}")
        fail_count += 1

print("=" * 60)
print(" 第 11 阶段扩展：商店系统冒烟测试")
print("=" * 60)

# [1] 商店 JSON 数据加载
print("\n[1] 商店数据加载")
import json
shop_path = os.path.join("data", "items", "shop_merchant.json")
with open(shop_path, encoding="utf-8") as f:
    shop_data = json.load(f)
check("categories" in shop_data, "categories 字段存在")
check(len(shop_data["categories"]) == 4, f"4 个分类: {len(shop_data['categories'])}")

cats = shop_data["categories"]
total_items = sum(len(c["items"]) for c in cats)
check(total_items >= 45, f"商品总数 >= 45: {total_items}")

# 验证所有 item_id 非空且价格 > 0
all_ok = True
for cat in cats:
    for item in cat["items"]:
        if not item.get("item_id") or item.get("price", 0) <= 0:
            all_ok = False
            print(f"    异常: {item}")
check(all_ok, "所有商品 item_id 和 price 有效")

# [2] ShopScreen 导入与创建
print("\n[2] ShopScreen 导入与创建")
from ui.shop_screen import ShopScreen
shop = ShopScreen()
check(shop is not None, "ShopScreen 实例化")
check(not shop.is_open, "初始未打开")
check(len(shop._categories) == 4, f"加载 4 个分类: {len(shop._categories)}")

# [3] ShopScreen 打开/关闭
print("\n[3] ShopScreen 打开/关闭")
from entities.player.player import Player
player = Player(100, 100)
player.soul_fragments = 2000

shop.open(player)
check(shop.is_open, "打开后 is_open=True")
check(shop._player is player, "绑定 player")
check(shop._category_idx == 0, "默认分类索引=0")
check(shop._item_idx == 0, "默认商品索引=0")

shop.close()
check(not shop.is_open, "关闭后 is_open=False")

# [4] 键盘导航：分类切换 Q/E
print("\n[4] 键盘导航")
shop.open(player)

# Q → 向左切换（到最后一个分类）
e_q = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_q})
shop.handle_event(e_q)
check(shop._category_idx == len(shop._categories) - 1, f"Q 切换→最后一个分类: {shop._category_idx}")

# E → 向右切换（回到第一个）
e_e = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_e})
shop.handle_event(e_e)
check(shop._category_idx == 0, f"E 切换→第一个分类: {shop._category_idx}")

# W/S 导航
e_w = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w})
shop.handle_event(e_w)  # 第一项 W 不变
check(shop._item_idx == len(shop._current_category()) - 1, "W 到末尾")

e_s = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s})
shop.handle_event(e_s)
check(shop._item_idx == 0, "S 回到开头")

# [5] 购买：草药汤（30魂）
print("\n[5] 购买消耗品")
player.soul_fragments = 2000
# 确认初始持有
inv = player.inventory
held_before = inv.count("heal_potion_small")
check(held_before >= 0, f"购买前持有: {held_before}")

# 执行购买（Enter键）
e_enter = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
shop.handle_event(e_enter)

# 验证
souls_after = player.soul_fragments
check(souls_after == 1970, f"扣款 30 魂: {souls_after} (expected 1970)")
held_after = inv.count("heal_potion_small")
check(held_after == held_before + 1, f"持有 +1: {held_before} → {held_after}")

# [6] 购买武器
print("\n[6] 购买武器")
# 切换到武器分类
shop._category_idx = 1
shop._item_idx = 0  # knight_sword

player.soul_fragments = 5000
held_before = inv.count("knight_sword")
shop.handle_event(e_enter)
souls_after = player.soul_fragments
check(souls_after == 4000, f"扣款 1000 魂: {souls_after}")
held_after = inv.count("knight_sword")
check(held_after == held_before + 1, f"武器持有 +1: {held_before} → {held_after}")

# [7] 购买护甲
print("\n[7] 购买护甲")
shop._category_idx = 2
shop._item_idx = 0  # knight_helm

player.soul_fragments = 3000
held_before = inv.count("knight_helm")
shop.handle_event(e_enter)
souls_after = player.soul_fragments
check(souls_after == 2500, f"扣款 500 魂: {souls_after}")
held_after = inv.count("knight_helm")
check(held_after == held_before + 1, f"护甲持有 +1: {held_before} → {held_after}")

# [8] 灵魂不足拒绝购买
print("\n[8] 灵魂不足")
player.soul_fragments = 10
shop._category_idx = 0
shop._item_idx = 0  # heal_potion_small = 30魂
held_before = inv.count("heal_potion_small")
shop.handle_event(e_enter)
souls_after = player.soul_fragments
check(souls_after == 10, f"灵魂未扣减: {souls_after}")
check("不足" in shop._message, f"提示消息含'不足': {shop._message}")

# [9] 已达上限
print("\n[9] 已达上限")
player.soul_fragments = 5000
# 先填满到 max_stack (10)
held = inv.count("heal_potion_small")
needed = 10 - held
if needed > 0:
    from items.item_database import item_db
    for _ in range(needed):
        it = item_db.create("heal_potion_small")
        inv.add(it, 1)

check(inv.count("heal_potion_small") == 10, f"已填满至 10: {inv.count('heal_potion_small')}")

shop.handle_event(e_enter)
check("已满" in shop._message or "上限" in shop._message, f"提示达上限: {shop._message}")
check(player.soul_fragments == 5000, "灵魂未扣减")

# [10] ESC 关闭
print("\n[10] ESC 关闭")
e_esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
shop.handle_event(e_esc)
check(not shop.is_open, "ESC 关闭商店")

# [11] 事件集成
print("\n[11] 事件集成")
from core.event_manager import event_manager
from scenes.game_scene import GameScene
gs = GameScene(area_id="area_graveyard")
check(hasattr(gs, "_shop_screen"), "GameScene 有 _shop_screen")
check(gs._shop_screen is not None, "_shop_screen 非 None")

# 结果
print(f"\n{'='*60}")
if fail_count == 0:
    print("  全部测试通过！商店系统 ✅")
else:
    print(f"  {fail_count} 项测试失败 ❌")
print(f"{'='*60}\n")

event_manager.clear()
pygame.quit()
