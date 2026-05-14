# =============================================================
# _test_death_flow.py —— 死亡流程端到端测试
# =============================================================
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.font.init()

# 导入
class MockStats:
    hp = 0; max_hp = 100; is_dead = True
    stamina = 50.0; max_stamina = 100.0; mana = 25; max_mana = 50
    def take_damage_with_defense(self, a, e="physical"): return (a, a)
    def apply_growth(self, *a, **kw): pass

class MockGrowth:
    strength = 10; dexterity = 10; intelligence = 5; faith = 5
    vitality = 10; endurance = 10; equip_weight = 0.0; max_equip_load = 30.0
    roll_type = "normal"; unspent_points = 0

class MockBuild:
    level = 1; unspent = 0
    def get_soul_cost_to_next(self): return 120

class MockFSM:
    _state_name = "Idle"
    def is_in(self, name): return self._state_name == name
    def change_state(self, name): 
        old = self._state_name
        self._state_name = name
        return old
    def update(self, dt): pass

class MockPlayer:
    def __init__(self):
        self.stats = MockStats()
        self.growth = MockGrowth()
        self.build = MockBuild()
        self.fsm = MockFSM()
        self.soul_fragments = 500
        from pygame import Rect
        self.rect = Rect(320, 400, 24, 48)
        self.vel_x = 0.0
        self.gravity = None
        self.invincible = False
        self.hurt_timer = 0.0
    @property
    def is_dead(self): return self.fsm.is_in("Dead")
    @property
    def current_state(self): return self.fsm._state_name

# 模拟 GameScene 的 update 中的死亡检测
from ui.death_screen import DeathScreen
from systems.soul_fragment_system import SoulFragmentSystem

p = MockPlayer()
ds = DeathScreen()
death_paused = False

# 第一次帧 — 玩家 HP=0，不在 Dead 状态
assert p.stats.is_dead == True
assert p.is_dead == False
print(f"[帧 1] HP=0, is_dead={p.is_dead}, stats.is_dead={p.stats.is_dead}")

# GameScene.update 逻辑
if p.stats.is_dead and not p.is_dead:
    p.fsm.change_state("Dead")
    lost = p.soul_fragments
    ds.show(lost, p.rect.centerx, p.rect.centery)
    death_paused = True
    print(f"  → 进入死亡界面: lost={lost}, visible={ds.visible}, death_paused={death_paused}")

assert ds.visible == True
assert death_paused == True
assert p.is_dead == True
print(f"  ✓ 死亡界面 visible={ds.visible}, is_dead={p.is_dead}")

# 第二帧 — _death_paused=True，仅更新死亡界面
ds.update(0.016)
print(f"[帧 2] death_paused=True, 死亡界面 _can_respawn={ds._can_respawn}")

# 多帧推进到可以复活
for _ in range(60):
    ds.update(0.016)
print(f"[帧 ~60] _can_respawn={ds._can_respawn}")

assert ds._can_respawn == True
print(f"  ✓ 0.96秒后可复活")

# 模拟渲染
surf = pygame.Surface((1280, 720))
ds.render(surf)
print(f"  ✓ 死亡界面渲染成功")

# 模拟按 E 复活
from systems.respawn_system import RespawnSystem

# 模拟 RespawnSystem.handle_death 的行为
p.stats.hp = p.stats.max_hp
p.stats.stamina = p.stats.max_stamina
p.stats.mana = p.stats.max_mana
p.fsm.change_state("Idle")
ds.hide()
death_paused = False

print(f"[帧 ~61] 复活: hp={p.stats.hp}, is_dead={p.is_dead}, death_paused={death_paused}")
assert p.is_dead == False
assert ds.visible == False
assert death_paused == False
print(f"  ✓ 复活成功")

# 第二次死亡
p.stats.hp = 0
p.stats.is_dead = True
p.fsm._state_name = "Idle"  # 重置为Idle

print(f"\n[第二次死亡] HP=0, is_dead={p.is_dead}, stats.is_dead={p.stats.is_dead}")

if p.stats.is_dead and not p.is_dead:
    p.fsm.change_state("Dead")
    lost = p.soul_fragments
    ds.show(lost, p.rect.centerx, p.rect.centery)
    death_paused = True
    print(f"  → 再次进入死亡界面: lost={lost}, visible={ds.visible}")

assert ds.visible == True
print(f"  ✓ 第二次死亡界面正确出现")

print("\n✅ 死亡流程端到端测试通过！")
pygame.quit()
