# =============================================================
# audio/sfx_player.py —— 音效播放器
#
# 订阅事件系统，在战斗事件触发时播放对应音效。
# 所有音效均为程序生成的占位波形（方波/噪声），
# 后续替换真实音频资源只需调用 replace_sound(name, filepath)。
#
# 核心功能：
#   - 6 种核心占位音效（hit_flesh / hit_metal / parry_clang /
#     dodge_woosh / magic_cast / footstep）
#   - 订阅事件总线，自动播放
#   - 多声道复用（最多 8 通道）
#   - 音量控制
#
# 事件 → 音效映射：
#   player_hurt        → hit_flesh
#   player_block_hit   → hit_metal
#   player_parry       → parry_clang
#   player_dodge       → dodge_woosh
#   weapon_art_used    → magic_cast
# =============================================================
from __future__ import annotations

import struct
import math
import logging
from typing import Dict, Optional, Tuple

import pygame

from core.event_manager import event_manager

logger = logging.getLogger(__name__)

# 音频参数
_SAMPLE_RATE = 22050
_BITS = 16
_MAX_AMP = 32767


# =============================================================
# 程序生成占位音效
# =============================================================

def _generate_sine(frequency: float, duration: float,
                   volume: float = 0.5) -> pygame.mixer.Sound:
    """生成正弦波音效。"""
    n_samples = int(_SAMPLE_RATE * duration)
    buf = bytearray(n_samples * 2)  # 16-bit = 2 bytes/sample
    amp = int(_MAX_AMP * volume)

    for i in range(n_samples):
        t = i / _SAMPLE_RATE
        value = int(amp * math.sin(2 * math.pi * frequency * t))
        struct.pack_into("<h", buf, i * 2, value)

    return pygame.mixer.Sound(buffer=bytes(buf))


def _generate_square(frequency: float, duration: float,
                     volume: float = 0.4) -> pygame.mixer.Sound:
    """生成方波音效（更有打击感）。"""
    n_samples = int(_SAMPLE_RATE * duration)
    buf = bytearray(n_samples * 2)
    amp = int(_MAX_AMP * volume)
    period = _SAMPLE_RATE / frequency

    for i in range(n_samples):
        value = amp if (i % int(period)) < (period / 2) else -amp
        struct.pack_into("<h", buf, i * 2, value)

    return pygame.mixer.Sound(buffer=bytes(buf))


def _generate_noise(duration: float, volume: float = 0.35) -> pygame.mixer.Sound:
    """生成白噪声。"""
    import random as _random
    n_samples = int(_SAMPLE_RATE * duration)
    buf = bytearray(n_samples * 2)
    amp = int(_MAX_AMP * volume)

    for i in range(n_samples):
        value = _random.randint(-amp, amp)
        struct.pack_into("<h", buf, i * 2, value)

    return pygame.mixer.Sound(buffer=bytes(buf))


def _generate_sweep(freq_start: float, freq_end: float, duration: float,
                    volume: float = 0.45) -> pygame.mixer.Sound:
    """生成扫频音效（用于弹反/魔法等）。"""
    n_samples = int(_SAMPLE_RATE * duration)
    buf = bytearray(n_samples * 2)
    amp = int(_MAX_AMP * volume)

    for i in range(n_samples):
        t = i / _SAMPLE_RATE
        ratio = t / duration
        freq = freq_start + (freq_end - freq_start) * ratio
        value = int(amp * math.sin(2 * math.pi * freq * t))

        # 包络：起始 full → 末尾衰减
        env = 1.0 - ratio * 0.7
        value = int(value * env)

        struct.pack_into("<h", buf, i * 2, value)

    return pygame.mixer.Sound(buffer=bytes(buf))


def _generate_hit_flesh() -> pygame.mixer.Sound:
    """打击肉体：低频方波 + 噪声混合，50ms。"""
    s1 = _generate_square(80, 0.05, volume=0.5)
    s2 = _generate_noise(0.03, volume=0.2)
    # 简单混合：返回方波为主（噪声效果通过叠加频道实现）
    return s1


def _generate_hit_metal() -> pygame.mixer.Sound:
    """打击金属：高频方波短促，40ms。"""
    return _generate_square(600, 0.04, volume=0.35)


def _generate_parry_clang() -> pygame.mixer.Sound:
    """弹反金属碰撞：800→400Hz 扫频 + 谐波，120ms。"""
    return _generate_sweep(800, 300, 0.12, volume=0.45)


def _generate_dodge_woosh() -> pygame.mixer.Sound:
    """翻滚风声：白噪声包络，80ms。"""
    s = _generate_noise(0.08, volume=0.25)
    return s


def _generate_magic_cast() -> pygame.mixer.Sound:
    """魔法吟唱：200→500Hz 上升扫频，150ms。"""
    return _generate_sweep(200, 500, 0.15, volume=0.4)


def _generate_footstep() -> pygame.mixer.Sound:
    """脚步：极短脉冲，15ms。"""
    return _generate_square(40, 0.015, volume=0.2)


# =============================================================
# 音效工厂
# =============================================================

_SFX_GENERATORS: Dict[str, callable] = {
    "hit_flesh":   _generate_hit_flesh,
    "hit_metal":   _generate_hit_metal,
    "parry_clang": _generate_parry_clang,
    "dodge_woosh": _generate_dodge_woosh,
    "magic_cast":  _generate_magic_cast,
    "footstep":    _generate_footstep,
}


# =============================================================
# SFXPlayer
# =============================================================

class SFXPlayer:
    """
    音效播放器。

    用法：
        sfx = SFXPlayer()
        sfx.initialize()                          # 初始化 mixer + 生成占位音效
        sfx.subscribe_events(event_manager)       # 订阅战斗事件
        sfx.set_volume(0.8)                       # 设置全局音量

        # 手动播放
        sfx.play("hit_flesh")

        # 替换真实音效
        sfx.replace_sound("hit_flesh", "assets/audio/sfx/hit.wav")

        # 场景退出时
        sfx.unsubscribe_all()
    """

    # 最大同时播放声道数
    MAX_CHANNELS = 8

    def __init__(self):
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._channels: list = []
        self._next_channel: int = 0
        self._volume: float = 0.7
        self._initialized: bool = False

        # 事件→音效 映射
        self._event_sound_map: Dict[str, str] = {
            "player_hurt":       "hit_flesh",
            "player_block_hit":  "hit_metal",
            "player_parry":      "parry_clang",
            "player_dodge":      "dodge_woosh",
            "weapon_art_used":   "magic_cast",
            "enemy_hit":         "hit_flesh",
        }

        # 已订阅事件列表（用于取消订阅）
        self._subscribed_events: list = []

    # ----------------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """初始化 pygame mixer + 生成占位音效。"""
        if self._initialized:
            return

        try:
            pygame.mixer.init(frequency=_SAMPLE_RATE, size=-_BITS, channels=1)
        except pygame.error as e:
            logger.warning("SFXPlayer: pygame.mixer 初始化失败: %s", e)
            return

        # 预留声道
        try:
            pygame.mixer.set_num_channels(self.MAX_CHANNELS)
            self._channels = [pygame.mixer.Channel(i) for i in range(self.MAX_CHANNELS)]
        except pygame.error:
            self._channels = []

        # 生成占位音效
        for name, generator in _SFX_GENERATORS.items():
            try:
                self._sounds[name] = generator()
            except Exception as e:
                logger.warning("SFXPlayer: 生成音效 '%s' 失败: %s", name, e)

        self._initialized = True
        logger.info("SFXPlayer: 初始化完成，已加载 %d 个音效", len(self._sounds))

    # ----------------------------------------------------------------
    # 音效管理
    # ----------------------------------------------------------------

    def play(self, name: str, volume: float = 1.0) -> None:
        """
        播放指定音效。

        :param name:   音效名称
        :param volume: 额外音量倍率（0.0~1.0），叠乘全局音量
        """
        if not self._initialized or not self._channels:
            return

        sound = self._sounds.get(name)
        if sound is None:
            return

        # 循环取可用声道
        for _ in range(self.MAX_CHANNELS):
            ch = self._channels[self._next_channel]
            self._next_channel = (self._next_channel + 1) % self.MAX_CHANNELS
            if not ch.get_busy():
                final_vol = max(0.0, min(1.0, self._volume * volume))
                ch.set_volume(final_vol)
                ch.play(sound)
                return

        # 所有声道忙：抢占最老的
        ch = self._channels[self._next_channel]
        self._next_channel = (self._next_channel + 1) % self.MAX_CHANNELS
        final_vol = max(0.0, min(1.0, self._volume * volume))
        ch.set_volume(final_vol)
        ch.play(sound)

    def replace_sound(self, name: str, filepath: str) -> bool:
        """
        用真实音频文件替换占位音效。

        :param name:     音效名称
        :param filepath: wav/ogg 文件路径
        :return:         是否成功
        """
        try:
            self._sounds[name] = pygame.mixer.Sound(filepath)
            logger.info("SFXPlayer: 音效 '%s' 已替换为 %s", name, filepath)
            return True
        except Exception as e:
            logger.warning("SFXPlayer: 替换音效 '%s' 失败: %s", name, e)
            return False

    def get_sound_names(self) -> list:
        """返回当前已加载的音效名称列表。"""
        return list(self._sounds.keys())

    # ----------------------------------------------------------------
    # 音量
    # ----------------------------------------------------------------

    def set_volume(self, volume: float) -> None:
        """设置全局音量 (0.0 ~ 1.0)。"""
        self._volume = max(0.0, min(1.0, volume))

    def get_volume(self) -> float:
        return self._volume

    # ----------------------------------------------------------------
    # 事件订阅
    # ----------------------------------------------------------------

    def subscribe_events(self, event_mgr=None) -> None:
        """
        订阅事件总线，自动播放对应音效。

        :param event_mgr: EventManager 实例，默认使用全局 event_manager
        """
        if event_mgr is None:
            event_mgr = event_manager

        for event_name, sound_name in self._event_sound_map.items():
            def _make_callback(sn=sound_name):
                def _cb(data: dict):
                    self.play(sn)
                return _cb
            event_mgr.subscribe(event_name, _make_callback())
            self._subscribed_events.append((event_name, _make_callback()))

        logger.info("SFXPlayer: 已订阅 %d 个事件", len(self._event_sound_map))

    def unsubscribe_all(self, event_mgr=None) -> None:
        """取消所有事件订阅。"""
        if event_mgr is None:
            event_mgr = event_manager

        for event_name, callback in self._subscribed_events:
            event_mgr.unsubscribe(event_name, callback)
        self._subscribed_events.clear()

    def stop_all(self) -> None:
        """立即停止所有声道。"""
        if not self._initialized:
            return
        pygame.mixer.stop()

    def __repr__(self) -> str:
        return (f"<SFXPlayer sounds={len(self._sounds)} "
                f"volume={self._volume:.1f}>")
