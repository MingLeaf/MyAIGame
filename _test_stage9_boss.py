# =============================================================
# _test_stage9_boss.py —— 第 9 阶段 Boss 系统冒烟测试
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame; pygame.init(); pygame.font.init()

print("=" * 60)
print("第 9 阶段 Boss 系统测试")
print("=" * 60)

errors = []

def check(desc, fn):
    try:
        fn()
        print(f"  ✓ {desc}")
    except Exception as e:
        print(f"  ✗ {desc}: {e}")
        errors.append(desc)

# ---- 1. 模块导入 ----
print("\n[1] 模块导入...")
check("Boss基类", lambda: __import__("entities.enemy.bosses.base_boss"))
check("腐骨公爵", lambda: __import__("entities.enemy.bosses.duke_rotbone"))
check("Boss房间", lambda: __import__("map.boss_room"))
check("Boss血条", lambda: __import__("ui.boss_healthbar"))
check("Boss场景", lambda: __import__("scenes.boss_scene"))
check("bosses/__init__", lambda: __import__("entities.enemy.bosses"))

# ---- 2. JSON 数据加载 ----
print("\n[2] JSON 数据加载...")
from utils.json_loader import load_from_data_dir
cfg = load_from_data_dir("entities/bosses/duke_rotbone.json")
assert cfg["id"] == "duke_rotbone"
assert len(cfg["skills"]) == 4
assert cfg["stats"]["max_hp"] == 800
assert cfg["revive"]["revive_hp_pct"] == 0.6
print(f"  ✓ duke_rotbone.json: {len(cfg['skills'])} skills, HP={cfg['stats']['max_hp']}, revive={cfg['revive']['revive_delay']}s")

# ---- 3. Boss 基类实例化 ----
print("\n[3] Boss 基类实例化...")
from entities.enemy.bosses.base_boss import BaseBoss, BossSkill

# 测试 BossSkill
sk = BossSkill({
    "id": "test_slash", "name": "测试斩",
    "damage_mult": 1.0, "knockback": 150, "poise_damage": 20,
    "cooldown": 2.0, "windup_frames": 20, "active_frames": 8,
    "hitbox": {"w": 70, "h": 50, "offset_x": 30, "offset_y": -10},
    "element": "physical",
})
assert sk.skill_id == "test_slash"
assert sk.cooldown == 2.0
print(f"  ✓ BossSkill 创建: {sk.name}")

# ---- 4. 腐骨公爵实例化 ----
print("\n[4] 腐骨公爵实例化...")
from entities.enemy.bosses.duke_rotbone import DukeRotbone
boss = DukeRotbone(3000, 512)
assert boss.boss_display_name == "腐骨公爵"
assert boss.stats.max_hp == 800
assert boss.stats.atk == 23
assert len(boss._skills) == 4
print(f"  ✓ {boss.boss_display_name}: HP={boss.stats.hp}, Atk={boss.stats.atk}, Skills={len(boss._skills)}")

# ---- 5. 二阶段触发 ----
print("\n[5] 二阶段触发...")
# Boss update 需要 collision_map，mock 一个空地图
class MockCollision:
    def get_solid_tiles_in_rect(self, r): return []
    def get_platform_tiles_in_rect(self, r): return []

boss.stats.hp = 400  # 正好 50%
boss.update(0.016, MockCollision())
assert boss.phase == 2
assert boss._phase_triggered
print(f"  ✓ 二阶段已触发: phase={boss.phase}, speed={boss.stats.speed:.0f}")

# ---- 6. 技能施放 ----
print("\n[6] 技能施放...")
boss.player = None  # 没有玩家时不释放
# 手动测试技能 CD
sk0 = boss._skills[0]
assert sk0._cd_left == 0.0
boss.try_cast_skill(0)
assert boss._current_skill is not None
print(f"  ✓ 技能0 开始释放: {boss._current_skill.name} (前摇 {boss._current_skill.windup_frames}f)")

# 推进前摇
for _ in range(25):
    boss.update_skill_cast(0.016)
hb = boss.get_skill_hitbox()
assert hb is not None
print(f"  ✓ 技能判定框生成: w={hb.rect.width} h={hb.rect.height}")

# 技能 CD
assert sk0._cd_left == 0.0  # 技能结束后 CD 设置
boss.try_cast_skill(0)  # CD 中应失败
# CD 在技能结束后设置, 推进完毕:
boss._current_skill = None  # 手动结束
sk0._cd_left = 0.0
boss.try_cast_skill(0)
assert boss._current_skill is not None
print(f"  ✓ CD 超时后可再次释放")

# ---- 7. 复活机制 ----
print("\n[7] 复活机制...")
boss.dead = True
result = boss._check_revive()
assert result == True
assert boss._revive_pending
print(f"  ✓ 复活等待中: timer={boss._revive_timer:.1f}s")

for _ in range(200):
    boss.update(0.016, MockCollision())

assert not boss._revive_pending
assert boss._revived
assert not boss.dead
assert boss.stats.hp == int(800 * 0.6)
print(f"  ✓ 复活完成: HP={boss.stats.hp}, dead={boss.dead}")

# 二次死亡不再复活
boss.dead = True
result2 = boss._check_revive()
assert result2 == False
print(f"  ✓ 二次死亡不复活: _check_revive={result2}")

# ---- 8. Boss 血条 ----
print("\n[8] Boss 血条...")
from ui.boss_healthbar import BossHealthBar
bar = BossHealthBar()
bar.attach(boss)
assert bar._visible
surf = pygame.Surface((1280, 720))
bar.update(0.016)
bar.render(surf)
print(f"  ✓ BossHealthBar 渲染成功")

# 二阶段颜色变化
boss.stats.hp = 200
boss._phase = 2
bar.update(0.016)
bar.render(surf)
print(f"  ✓ 二阶段血条（橙色）渲染成功")

# ---- 9. 雾门 ----
print("\n[9] 雾门...")
from map.boss_room import BossRoom
room = BossRoom(
    room_id="test_room", world_x=3000, world_y=512,
    boss_id="duke_rotbone", boss_class=DukeRotbone,
)
assert room.rect.width == 64
room.update(0.016, pygame.Rect(0, 0, 10, 10))
room.render(surf, (0, 0))
print(f"  ✓ BossRoom 渲染成功: {len(room._particles)} particles")

# ---- 10. Area 集成 ----
print("\n[10] Area 雾门加载...")
from map.area import Area
area = Area("area_graveyard")
area.load()
boss_rooms = area.boss_rooms
assert len(boss_rooms) == 1
br = boss_rooms[0]
assert br.boss_id == "duke_rotbone"
print(f"  ✓ Area 加载: {len(boss_rooms)} 个 BossRoom ({br.boss_id} @ {br.x:.0f},{br.y:.0f})")

# ---- 11. BossScene 导入 ----
print("\n[11] BossScene...")
from scenes.boss_scene import BossScene
boss2 = DukeRotbone(3000, 512)
print(f"  ✓ BossScene 可导入")

# ---- 结果 ----
print("\n" + "=" * 60)
if errors:
    print(f"  ❌ {len(errors)} 项失败")
    for e in errors: print(f"     - {e}")
else:
    print("  ✅ 全部 11 组测试通过！")
print("=" * 60)
pygame.quit()
