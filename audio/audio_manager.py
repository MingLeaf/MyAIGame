# =============================================================
# audio/audio_manager.py —— 音频系统统一入口
#
# AudioManager 持有 SFXPlayer 和 BGMPlayer，提供一键初始化、
# 场景切换、音量调节等便捷方法。
#
# 用法：
#     audio = AudioManager()
#     audio.initialize()
#
#     # 场景 on_enter
#     audio.play_bgm("area_graveyard")
#
#     # 每帧（BGM 不需要，SFX 已通过事件自动触发）
#
#     # 音量设置（供 UI 设置面板调用）
#     audio.set_sfx_volume(0.8)
#     audio.set_bgm_volume(0.6)
#
#     # 场景 on_exit
#     audio.stop_bgm()
# =============================================================
from __future__ import annotations

import logging
from typing import Optional

from audio.sfx_player import SFXPlayer
from audio.bgm_player import BGMPlayer
from core.event_manager import event_manager

logger = logging.getLogger(__name__)


class AudioManager:
    """
    音频系统统一入口。

    创建后持有 SFXPlayer 和 BGMPlayer 两个子模块，
    外部只需持有 AudioManager 即可控制所有音频。
    """

    def __init__(self):
        self.sfx: SFXPlayer = SFXPlayer()
        self.bgm: BGMPlayer = BGMPlayer()
        self._initialized: bool = False

    # ----------------------------------------------------------------
    # 初始化 / 销毁
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """
        初始化音频系统：生成占位音效 + 订阅事件 + 初始化 BGM。

        应在游戏主循环开始前调用一次。
        """
        if self._initialized:
            return

        self.sfx.initialize()
        self.bgm.initialize()

        # 订阅战斗事件 → 自动播放音效
        self.sfx.subscribe_events(event_manager)

        self._initialized = True
        logger.info("AudioManager: 音频系统初始化完成")

    def shutdown(self) -> None:
        """关闭音频系统，取消事件订阅。"""
        self.sfx.unsubscribe_all(event_manager)
        self.bgm.stop(fade_ms=500)
        self._initialized = False
        logger.info("AudioManager: 音频系统已关闭")

    # ----------------------------------------------------------------
    # SFX 便捷接口
    # ----------------------------------------------------------------

    def play_sfx(self, name: str, volume: float = 1.0) -> None:
        """手动播放一个音效。"""
        self.sfx.play(name, volume)

    def set_sfx_volume(self, volume: float) -> None:
        """设置音效音量 (0.0~1.0)。"""
        self.sfx.set_volume(volume)

    def replace_sfx(self, name: str, filepath: str) -> bool:
        """替换占位音效为真实音频文件。"""
        return self.sfx.replace_sound(name, filepath)

    # ----------------------------------------------------------------
    # BGM 便捷接口
    # ----------------------------------------------------------------

    def register_bgm(self, area_id: str, filepath: str) -> None:
        """注册区域 BGM 文件。"""
        self.bgm.register_bgm(area_id, filepath)

    def register_bgm_from_config(self, config: dict) -> None:
        """从配置字典批量注册 BGM。"""
        self.bgm.register_from_config(config)

    def play_bgm(self, area_id: str, fade_ms: int = 1500) -> None:
        """
        播放区域 BGM。

        如果 area.bgm_id 有值则用它，否则用 area_id。
        无音频文件时静默运行，不报错。
        """
        self.bgm.play(area_id, fade_ms=fade_ms)

    def crossfade_bgm(self, area_id: str, fade_ms: int = 1500) -> None:
        """交叉淡入淡出切换 BGM。"""
        self.bgm.crossfade(area_id, fade_ms=fade_ms)

    def stop_bgm(self, fade_ms: int = 1000) -> None:
        """停止 BGM（带淡出）。"""
        self.bgm.stop(fade_ms=fade_ms)

    def set_bgm_volume(self, volume: float) -> None:
        """设置 BGM 音量 (0.0~1.0)。"""
        self.bgm.set_volume(volume)

    # ----------------------------------------------------------------
    # 全系统控制
    # ----------------------------------------------------------------

    def pause_all(self) -> None:
        """暂停所有音频（进入暂停菜单时）。"""
        self.bgm.pause()
        self.sfx.stop_all()

    def resume_all(self) -> None:
        """恢复所有音频（退出暂停菜单时）。"""
        self.bgm.unpause()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def __repr__(self) -> str:
        return f"<AudioManager sfx={self.sfx} bgm={self.bgm}>"
