# =============================================================
# animation/__init__.py —— 动画系统统一导出
# =============================================================

from animation.animation_clip import AnimationClip
from animation.sprite_sheet_loader import SpriteSheetLoader
from animation.animation_state_machine import AnimationStateMachine
from animation.animator import Animator
from animation.particle_system import (
    Particle, ParticleEmitter, ParticleManager,
    PresetEmitters,
)

__all__ = [
    "AnimationClip",
    "SpriteSheetLoader",
    "AnimationStateMachine",
    "Animator",
    "Particle",
    "ParticleEmitter",
    "ParticleManager",
    "PresetEmitters",
]
