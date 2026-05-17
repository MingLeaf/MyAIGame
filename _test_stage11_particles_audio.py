# =============================================================
# _test_stage11_particles_audio.py —— 第 11 阶段冒烟测试
#
# 测试项：
#   [1] 粒子系统：Particle 创建/更新/渲染 → 无崩溃
#   [2] 粒子发射器：8 种预设发射 + 依附/屏幕空间 → 无崩溃
#   [3] ParticleManager：全局管理 + spawn/attach/remove → 无崩溃
#   [4] 动画系统：AnimationClip/Animator/StateMachine → 导入无异常
#   [5] 音效系统：占位波形生成 + SFXPlayer 初始化 → 无异常
#   [6] BGM 系统：BGMPlayer 初始化/静默模式 → 无崩溃
#   [7] AudioManager：统一入口创建 + 事件订阅 → 无异常
#   [8] StatusManager 事件：status_applied/status_removed → 事件正确发射
#   [9] 场景集成：GameScene/BossScene 粒子+音频字段 → 无崩溃
#  [10] HitResolver 事件：enemy_hit 事件发射 → 正确连接
#
# 运行方式：
#   python _test_stage11_particles_audio.py
#   或 SDL_VIDEODRIVER=dummy python _test_stage11_particles_audio.py
# =============================================================
import os
import sys
import time

# 禁用音频（避免无音频设备崩溃）
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()

# 设置一个最小窗口（dummy 也需要 surface）
pygame.display.set_mode((320, 240))


def log(msg: str) -> None:
    print(f"  {msg}")


def test_header(name: str) -> None:
    print(f"\n{'='*60}")
    print(f" 测试 [{name}]")
    print(f"{'='*60}")


fail_count = 0


def check(condition: bool, label: str) -> None:
    global fail_count
    if condition:
        print(f"    PASS  {label}")
    else:
        print(f"    FAIL  {label}")
        fail_count += 1


# =============================================================
# [1] Particle 创建/更新/渲染
# =============================================================
test_header("1  Particle 单颗粒子")

from animation.particle_system import Particle

p = Particle(x=100, y=100, vx=50, vy=-120, lifetime=1.0,
             color=(255, 60, 60), size=5, gravity=300)
check(p.is_alive, "粒子创建后存活")

# 更新 0.5s
p.update(0.5)
check(p.is_alive, "0.5s 后仍存活")
check(p.elapsed == 0.5, f"elapsed={p.elapsed:.1f}")
check(p.alpha < 255, f"alpha 已衰减: {p.alpha}")

# 更新至过期
p.update(0.6)
check(not p.is_alive, "1.1s 后死亡")

# 渲染（不崩溃即可）
surf = pygame.Surface((320, 240))
p.render(surf, 0, 0)  # 死亡粒子不渲染，不抛异常

# 纹理替换接口
p2 = Particle(x=0, y=0, lifetime=1.0, color=(255, 255, 255), size=10,
              texture=pygame.Surface((16, 16)))
p2.texture.fill((255, 0, 0))
p2.render(surf, 0, 0)
check(True, "纹理模式渲染无崩溃")


# =============================================================
# [2] ParticleEmitter 8种预设
# =============================================================
test_header("2  ParticleEmitter 预设发射器")

from animation.particle_system import ParticleEmitter, PresetEmitters

presets = {
    "blood_splash":   PresetEmitters.blood_splash,
    "parry_flash":    PresetEmitters.parry_flash,
    "poison_bubbles": PresetEmitters.poison_bubbles,
    "burn_fire":      PresetEmitters.burn_fire,
    "freeze_crystals": PresetEmitters.freeze_crystals,
    "bleed_drip":     PresetEmitters.bleed_drip,
    "dust_cloud":     PresetEmitters.dust_cloud,
    "magic_spark":    PresetEmitters.magic_spark,
}

for name, factory in presets.items():
    emitter = factory()
    check(emitter is not None, f"预设 '{name}' 创建成功")
    check(emitter.name != "", f"预设 '{name}' 有名称")

# 发射测试
em = PresetEmitters.blood_splash()
em.emit(count=8, position=(100, 100))
check(em.alive_count == 8, f"发射 8 颗粒子: {em.alive_count}")

# 更新 30 帧 (~0.5s)
for _ in range(30):
    em.update(1 / 60)
check(em.alive_count <= 8, f"更新后粒子数: {em.alive_count}")

# 依附模式
class FakeEntity:
    def __init__(self):
        self.x = 200.0
        self.y = 300.0
        self.rect = pygame.Rect(180, 280, 40, 60)

fake = FakeEntity()
em2 = PresetEmitters.burn_fire(attach_entity=fake)
em2.emit(count=3)
check(em2.attach_entity is fake, "依附实体设置正确")
em2.update(0.1)

# 屏幕空间
em3 = PresetEmitters.parry_flash()
check(em3.screen_space, "弹反闪光为屏幕空间")

# continuous 发射器
em4 = PresetEmitters.poison_bubbles(attach_entity=fake)
check(em4.continuous, "中毒发射器为连续模式")
em4.update(1.0)
check(em4.alive_count > 0, f"连续发射 1s 后粒子数: {em4.alive_count}")


# =============================================================
# [3] ParticleManager
# =============================================================
test_header("3  ParticleManager 全局管理")

from animation.particle_system import ParticleManager

mgr = ParticleManager()

# spawn
e1 = mgr.spawn("blood_splash", position=(150, 200))
check(e1 is not None, "spawn blood_splash 成功")
check(mgr.emitter_count == 1, f"发射器数: {mgr.emitter_count}")

# spawn screen_space
e2 = mgr.spawn("parry_flash", screen_pos=(160, 120))
check(e2 is not None and e2.screen_space, "spawn parry_flash 屏幕空间")

# attach
e3 = mgr.attach("poison", entity=fake)
check(e3 is not None, "attach poison 成功")
check(mgr.emitter_count == 3, f"挂载后发射器数: {mgr.emitter_count}")

# update
for _ in range(60):
    mgr.update(1 / 60)
check(mgr.total_particles >= 0, f"更新后总粒子: {mgr.total_particles}")

# remove_attached
mgr.remove_attached("poison", entity=fake)
# 自动清理后
mgr.update(1.0)
check(True, "remove_attached 无崩溃")

# render
surf = pygame.Surface((320, 240))
mgr.render(surf, 0, 0)
check(True, "render 无崩溃")

# clear
mgr.clear()
check(mgr.emitter_count == 0, f"clear 后发射器数: {mgr.emitter_count}")


# =============================================================
# [4] 动画系统导入
# =============================================================
test_header("4  动画系统导入与实例化")

from animation.animation_clip import AnimationClip
from animation.sprite_sheet_loader import SpriteSheetLoader
from animation.animation_state_machine import AnimationStateMachine
from animation.animator import Animator

# AnimationClip
clip = AnimationClip.placeholder(frame_count=4, frame_rate=12.0,
                                  size=(32, 32), color=(100, 200, 100))
check(clip.frame_count == 4, f"帧数: {clip.frame_count}")
surf, idx = clip.get_frame(0.0)
check(surf is not None, "第 0 帧返回非 None")
check(idx == 0, f"帧索引: {idx}")
surf, idx = clip.get_frame(0.5)
check(idx >= 0, f"0.5s 帧索引: {idx}")

# SpriteSheetLoader
loader = SpriteSheetLoader()
check(loader is not None, "SpriteSheetLoader 创建成功")

# AnimationStateMachine
asm = AnimationStateMachine()
asm.register_placeholder("Idle", frame_count=4, color=(150, 150, 150))
asm.register_placeholder("Run",  frame_count=6, color=(100, 200, 100))
asm.set_state("Idle")
check(asm.get_current_state() == "Idle", f"当前状态: {asm.get_current_state()}")
asm.update(0.5)
clip = asm.get_clip()
check(clip is not None, "getIdle clip非None")

# Animator
anim = Animator()
anim.register_placeholder("Idle", frame_count=4, color=(150, 150, 150))
anim.set_state("Idle")
anim.update(0.1, facing=-1)
check(anim.flip_x, "facing=-1 时 flip_x=True")
surf = anim.get_current_frame()
check(surf is not None, "get_current_frame 非None")


# =============================================================
# [5] 音效系统
# =============================================================
test_header("5  SFXPlayer 音效生成")

from audio.sfx_player import SFXPlayer

sfx = SFXPlayer()
sfx.initialize()
names = sfx.get_sound_names()
check(len(names) >= 5, f"已生成音效数: {len(names)}")

# 播放（dummy 音频驱动下不会报错）
sfx.play("hit_flesh")
sfx.play("parry_clang")
check(True, "play 音效无崩溃")

# 音量
sfx.set_volume(0.5)
check(abs(sfx.get_volume() - 0.5) < 0.01, f"音量设置: {sfx.get_volume():.1f}")


# =============================================================
# [6] BGM 系统
# =============================================================
test_header("6  BGMPlayer 静默模式")

from audio.bgm_player import BGMPlayer

bgm = BGMPlayer()
bgm.initialize()
check(bgm._initialized, "BGMPlayer 初始化")

# 无文件 → 静默
bgm.play("area_graveyard")
check(bgm.current_area == "area_graveyard", f"当前区域: {bgm.current_area}")

# 注册自定义 BGM（文件不存在 → 静默）
bgm.register_bgm("area_test", "nonexistent.ogg")
bgm.play("area_test")
check(bgm.current_area == "area_test", "未找到文件保持静默")

# 淡出停止
bgm.stop(fade_ms=0)
check(True, "stop 无崩溃")


# =============================================================
# [7] AudioManager 统一入口
# =============================================================
test_header("7  AudioManager 统一入口")

from audio.audio_manager import AudioManager

audio = AudioManager()
audio.initialize()
check(audio.is_initialized, "AudioManager 初始化")

audio.play_sfx("hit_flesh")
check(True, "play_sfx 无崩溃")

audio.play_bgm("area_graveyard")
check(True, "play_bgm 无崩溃")

audio.pause_all()
audio.resume_all()
check(True, "pause/resume 无崩溃")

audio.stop_bgm(fade_ms=0)


# =============================================================
# [8] StatusManager 事件
# =============================================================
test_header("8  StatusManager status_applied/removed 事件")

from core.event_manager import event_manager
from combat.status_manager import StatusManager
from combat.status_effect import PoisonEffect, BleedEffect

received_events = []

def _on_status(data):
    received_events.append(data)

event_manager.subscribe("status_applied", _on_status)
event_manager.subscribe("status_removed", _on_status)

class FakeStats:
    def __init__(self):
        self.hp = 100
        self.max_hp = 100
    def take_damage(self, dmg):
        self.hp -= dmg

fake2 = type("FakeEnt", (), {
    "x": 100.0, "y": 100.0,
    "rect": pygame.Rect(80, 80, 40, 60),
    "stats": FakeStats(),
    "frozen": False,
    "stunned": False,
    "_on_dot_damage": lambda self, dmg, t: None,
    "_on_bleed_burst": lambda self, dmg: None,
})()

stm = StatusManager(fake2)
stm.add(PoisonEffect(duration=5))
check(len(received_events) >= 1, f"status_applied 事件触发: {len(received_events)}")
check(received_events[-1]["status"] == "poison", f"事件状态名: {received_events[-1]['status']}")

stm.remove("poison")
check(len(received_events) >= 2, f"status_removed 事件触发: {len(received_events)}")
check(received_events[-1]["status"] == "poison", f"移除事件状态名: {received_events[-1]['status']}")

event_manager.unsubscribe("status_applied", _on_status)
event_manager.unsubscribe("status_removed", _on_status)


# =============================================================
# [9] 场景集成
# =============================================================
test_header("9  GameScene / BossScene 粒子+音频字段")

from scenes.game_scene import GameScene

# 仅测试构造不崩溃（不实际 on_enter）
gs = GameScene(area_id="area_graveyard")
check(hasattr(gs, "_particle_mgr"), "GameScene 有 _particle_mgr")
check(hasattr(gs, "_audio_mgr"), "GameScene 有 _audio_mgr")
check(gs._particle_mgr is not None, "_particle_mgr 非 None")
check(gs._audio_mgr is not None, "_audio_mgr 非 None")


# =============================================================
# [10] HitResolver enemy_hit 事件
# =============================================================
test_header("10  HitResolver enemy_hit 事件连接")

from combat.hit_resolver import _post_hit_sound

hit_events = []
def _on_enemy_hit(data):
    hit_events.append(data)

event_manager.subscribe("enemy_hit", _on_enemy_hit)

# 调用旧接口 → 应触发 enemy_hit 事件
_post_hit_sound("hit_flesh")
check(len(hit_events) >= 1, f"enemy_hit 事件触发: {len(hit_events)}")
check(hit_events[-1]["sound"] == "hit_flesh", f"sound 字段: {hit_events[-1]['sound']}")

event_manager.unsubscribe("enemy_hit", _on_enemy_hit)


# =============================================================
# 结果
# =============================================================
print(f"\n{'='*60}")
if fail_count == 0:
    print("  全部测试通过！第 11 阶段冒烟测试 ✅")
else:
    print(f"  {fail_count} 项测试失败 ❌")
print(f"{'='*60}\n")

event_manager.clear()
pygame.quit()
sys.exit(0 if fail_count == 0 else 1)
