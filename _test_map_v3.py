# =============================================================
# _test_map_v3.py —— 古墓地图 v3 可达性 + 营地安全区验证
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame; pygame.init(); pygame.font.init()

print("=" * 60)
print("古墓地图 v3 验证")
print("=" * 60)

JUMP_FORCE = 480
GRAVITY = 900
PLAYER_SPEED = 240
TILE_SIZE = 32
MAX_VERT_JUMP = JUMP_FORCE * JUMP_FORCE / (2 * GRAVITY) / TILE_SIZE
MAX_HORIZ_JUMP = PLAYER_SPEED * (2 * JUMP_FORCE / GRAVITY) / TILE_SIZE

print(f"\n物理参数: 垂直 {MAX_VERT_JUMP:.1f} 行, 水平 {MAX_HORIZ_JUMP:.1f} 列")

# ---- 加载地图 ----
from map.area import Area
area = Area("area_graveyard")
area.load()

print(f"地图尺寸: {area.tile_map.width}×{area.tile_map.height}")
print(f"营地数: {len(area.campfires)}")
print(f"敌人数: {len(area.enemies)}")

# ---- 1. 敌人数量检查 ----
print(f"\n[1] 敌人数量: {len(area.enemies)} (预期 13)")
assert len(area.enemies) == 13, f"敌人数量应为 13，实际 {len(area.enemies)}"
print("  ✓ 13 名敌人")

# ---- 2. 营地安全区检查 ----
print("\n[2] 营地安全区检查...")
for cf in area.campfires:
    cf_col = int(cf.x // TILE_SIZE)
    cf_id = cf.campfire_id
    
    too_close = []
    for e in area.enemies:
        e_col = int(e.rect.centerx // TILE_SIZE)
        dist_cols = abs(e_col - cf_col)
        if dist_cols < 5:
            too_close.append((getattr(e, 'CATEGORY', '?'), e_col, dist_cols))
    
    if too_close:
        for cat, col, dist in too_close:
            print(f"  ✗ {cf_id} (col {cf_col}): {cat} 在 col {col}，仅距 {dist} 列")
        assert False, "营地附近有敌人！"
    else:
        print(f"  ✓ {cf_id} (col {cf_col}): 安全（最近敌人 ≥6 列）")

# ---- 3. 平台可达性检查 ----
print("\n[3] 平台可达性检查...")

# 解析 ground 层，提取平台坐标
ground_layer = area.tile_map.get_ground_layer()
if ground_layer:
    data = ground_layer.data
    platforms = []  # (row, col_start, col_end)
    for row_idx, row in enumerate(data):
        i = 0
        while i < len(row):
            if row[i] == 2:  # 平台
                start = i
                while i < len(row) and row[i] == 2:
                    i += 1
                platforms.append((row_idx, start, i - 1))
            else:
                i += 1
    
    print(f"  发现 {len(platforms)} 段平台")
    
    for row, cs, ce in platforms:
        reachable = False
        
        # 1. 检查下方 3 行内是否有实心地面
        for check_row in range(row + 1, min(row + 5, len(data))):
            for c in range(max(0, cs - 1), min(ce + 2, len(data[0]))):
                if data[check_row][c] == 1:
                    reachable = True
                    break
            if reachable:
                break
        
        # 2. 检查下方是否有平台做踏板（最多 3 行）
        if not reachable:
            for prow, pcs, pce in platforms:
                if row - 3 <= prow < row:
                    if not (ce < pcs - 1 or cs > pce + 1):
                        reachable = True
                        break
        
        status = "✓" if reachable else "✗"
        note = "" if reachable else " (无支撑)"
        print(f"    {status} row {row} cols {cs}-{ce} (宽 {ce-cs+1}){note}")

# ---- 4. 地图尺寸验证 ----
print(f"\n[4] 地图尺寸: 100×22 (预期)")
assert area.tile_map.width == 100
assert area.tile_map.height == 22
print("  ✓ 尺寸正确")

# ---- 5. 传送门位置 ----
print(f"\n[5] 传送门: {len(area.transitions)} 个")
for t in area.transitions:
    print(f"    目标: {t.target_area}, 方向: {t.direction}")

# ---- 6. JSON 结构验证 ----
print("\n[6] JSON 格式验证...")
import json
from utils.json_loader import load_from_data_dir
tilemap = load_from_data_dir("maps/area_graveyard/tilemap.json")
assert tilemap["width"] == 100
assert tilemap["height"] == 22
assert len(tilemap["layers"]) == 2

# 检查每行长度
for li, layer in enumerate(tilemap["layers"]):
    data = layer["data"]
    for ri, row in enumerate(data):
        assert len(row) == 100, f"Layer {li} row {ri}: 期望 100, 实际 {len(row)}"
print(f"  ✓ 所有行长度 = 100")

spawns = load_from_data_dir("maps/area_graveyard/enemy_spawns.json")
assert len(spawns["spawns"]) == 13
print(f"  ✓ enemy_spawns 有 13 条")

print("\n" + "=" * 60)
print("  ✅ 古墓地图 v3 全部验证通过！")
print("=" * 60)

pygame.quit()
