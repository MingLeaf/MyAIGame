# =============================================================
# _test_stage10_npc.py —— 第 10 阶段 NPC 冒烟测试
# =============================================================

import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()

print("="*50)
print("第 10 阶段 NPC 系统 · 冒烟测试")
print("="*50)

# ---- 1. 验证地图 NPC 配置 ----
print("\n[1] 地图 NPC 配置验证")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "data", "maps", "area_graveyard")

with open(os.path.join(BASE, "tilemap.json"), encoding="utf-8") as f:
    tm = json.load(f)

npcs = tm["objects"].get("npcs", [])
assert len(npcs) == 3, f"应该有 3 个 NPC，实际 {len(npcs)}"
types = {n["type"] for n in npcs}
assert types == {"keeper", "blacksmith", "merchant"}, f"NPC 类型不对: {types}"
print(f"  ✓ 3 个 NPC 配置正确: {types}")

# 验证安全区
with open(os.path.join(BASE, "enemy_spawns.json"), encoding="utf-8") as f:
    es = json.load(f)

cf = {c["id"]: c["x"] for c in tm["objects"]["campfires"]}
for npc in npcs:
    nx = npc["x"]
    min_dist = min(abs(s["x"] - nx) for s in es["spawns"])
    assert min_dist >= 12, f"NPC {npc['type']} col {nx} 距最近敌人仅 {min_dist} 格"
print(f"  ✓ 所有 NPC 安全区 ≥12 格")

# ---- 2. NPC 实例化 ----
print("\n[2] NPC 实例化")
from entities.npc.base_npc import BaseNPC, create_npc

keeper = create_npc("keeper", "test_keeper", 300, 500)
blacksmith = create_npc("blacksmith", "test_smith", 600, 500)
merchant = create_npc("merchant", "test_merchant", 900, 500)

assert isinstance(keeper, BaseNPC)
assert isinstance(blacksmith, BaseNPC)
assert isinstance(merchant, BaseNPC)
assert keeper.display_name == "守护者 艾德"
assert blacksmith.display_name == "铁匠 多兰"
assert merchant.display_name == "商人 莉亚"
print(f"  ✓ 3 类 NPC 实例化成功")

# 回退情况
unknown = create_npc("unknown_type", "test_x", 0, 0)
assert isinstance(unknown, BaseNPC)
assert "未知" in unknown.display_name
print(f"  ✓ 未知类型回退为 BaseNPC")

# ---- 3. 对话数据加载 ----
print("\n[3] 对话数据加载")
from utils.json_loader import load_from_data_dir

keeper_dia = load_from_data_dir("dialogues/npc_keeper.json")
assert keeper_dia is not None
assert "start_node" in keeper_dia
assert "nodes" in keeper_dia
assert "greeting" in keeper_dia["nodes"]
print(f"  ✓ keeper 对话数据加载成功 ({len(keeper_dia['nodes'])} 节点)")

smith_dia = load_from_data_dir("dialogues/npc_blacksmith.json")
assert smith_dia is not None
assert "greeting" in smith_dia["nodes"]
print(f"  ✓ blacksmith 对话数据加载成功 ({len(smith_dia['nodes'])} 节点)")

merchant_dia = load_from_data_dir("dialogues/npc_merchant.json")
assert merchant_dia is not None
assert "greeting" in merchant_dia["nodes"]
print(f"  ✓ merchant 对话数据加载成功 ({len(merchant_dia['nodes'])} 节点)")

# ---- 4. 对话引擎 ----
print("\n[4] 对话引擎")

from core.dialogue_engine import DialogueEngine

actions_called = []
def record_action(data):
    actions_called.append(data.get("choice", {}).get("action", "unknown"))

engine = DialogueEngine(keeper_dia, {
    "open_level_up": record_action,
    "open_teleport": record_action,
    "chat": record_action,
})
assert engine.start()
assert "流浪者" in engine.current_text
assert len(engine.current_choices) > 0
print(f"  ✓ 对话引擎启动成功: '{engine.current_text[:20]}...'")

# 选择第 0 项
engine.select_choice(0)
assert len(actions_called) > 0
assert actions_called[0] == "open_level_up"
print(f"  ✓ 选项 0 触发动作: {actions_called[0]}")

assert engine.is_active  # 跳转到了 after_levelup
print(f"  ✓ 跳转成功: '{engine.current_text[:20]}...'")

# 选择最后一项结束对话
while engine.is_active:
    choices = engine.current_choices
    if not choices:
        break
    # 选择最后一项 (通常是退出)
    engine.select_choice(len(choices) - 1)

assert not engine.is_active
print(f"  ✓ 对话正常结束")

# ---- 5. 对话框 UI 类 ----
print("\n[5] 对话框 UI")

from ui.dialogue_box import DialogueBox
dlg = DialogueBox()
assert not dlg.is_open()

engine2 = DialogueEngine(keeper_dia, {"open_level_up": lambda d: None})
engine2.start()
dlg.open(engine2, "守护者 艾德")
assert dlg.is_open()
assert dlg._engine is engine2
print(f"  ✓ 对话框打开成功")

# 模拟按键事件快进
fake_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
result = dlg.handle_event(fake_event)
assert result  # 被消耗
print(f"  ✓ 对话框事件处理正常")

dlg.close()
assert not dlg.is_open()
print(f"  ✓ 对话框关闭成功")

# ---- 6. Area NPC 加载 ----
print("\n[6] Area NPC 加载")

from map.area import Area
area = Area("area_graveyard")
area.load()
assert len(area.npcs) == 3
for npc in area.npcs:
    assert isinstance(npc, BaseNPC)
print(f"  ✓ Area 加载了 {len(area.npcs)} 个 NPC")

# ---- 7. 交互检测 ----
print("\n[7] 交互检测")

keeper_npc = area.npcs[0]
player_rect = pygame.Rect(
    keeper_npc.x - 20, keeper_npc.y - 60, 40, 60
)
keeper_npc.update(0.016, player_rect)
assert keeper_npc.is_near()
print(f"  ✓ 玩家靠近 NPC 时交互检测正常")

far_rect = pygame.Rect(9999, 9999, 40, 60)
keeper_npc.update(0.016, far_rect)
assert not keeper_npc.is_near()
print(f"  ✓ 玩家远离 NPC 时不触发交互")

# ---- 8. BossScene 无 NPC ----
print("\n[8] BossScene 无 NPC")

boss_area = Area("boss_duke")
# 不加载，只检查 npcs 字段为空
assert boss_area.npcs == []
print(f"  ✓ Boss 场景无 NPC 干扰")

# ---- 9. 工厂函数覆盖 ----
print("\n[9] 工厂函数完整覆盖")

for t, cls_name in [("keeper", "KeeperNPC"), ("blacksmith", "BlacksmithNPC"),
                     ("merchant", "MerchantNPC")]:
    npc = create_npc(t, f"test_{t}", 0, 0)
    assert cls_name in type(npc).__name__, f"{t} NPC 类型应为 {cls_name}"
print(f"  ✓ 工厂函数 3 种类型全部映射正确")

# ---- 10. 会话动作注册 ----
print("\n[10] NPC 动作回调")

keeper = create_npc("keeper", "k1", 0, 0)
actions = keeper.get_actions()
assert "open_level_up" in actions
assert "open_teleport" in actions
assert "chat" in actions
print(f"  ✓ keeper 注册了 {len(actions)} 个动作")

smith = create_npc("blacksmith", "b1", 0, 0)
actions = smith.get_actions()
assert "open_weapon_upgrade" in actions
print(f"  ✓ blacksmith 注册了 {len(actions)} 个动作")

mer = create_npc("merchant", "m1", 0, 0)
actions = mer.get_actions()
assert "open_shop" in actions
print(f"  ✓ merchant 注册了 {len(actions)} 个动作")

# ---- 完成 ----
print("\n" + "="*50)
print("✅ 第 10 阶段 NPC 系统全部 10 项测试通过！")
print("="*50)

pygame.quit()
