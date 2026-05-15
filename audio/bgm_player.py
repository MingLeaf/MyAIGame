# =============================================================
# audio/bgm_player.py —— 背景音乐播放器
#
# 负责区域 BGM 的播放、淡入淡出切换。
# 暂无真实音频文件时以静默模式运行（仅 logger 提示），
# 不中断游戏流程。
#
# 功能：
#   - play(area_id) → 根据区域 ID 选择 BGM 并淡入
#   - stop(fade_ms) → 淡出并停止
#   - crossfade(area_id, fade_ms) → 交叉淡入淡出
#   - 区域 BGM 映射表可配置
#
# 资源替换接口：
#   - register_bgm(area_id, filepath) ：注册自定义 BGM 文件
#   - bgm_map 字典可直接从 JSON 配置文件加载
# =============================================================
from __future__ import annotations

import os
import logging
from typing import Dict, Optional

import pygame

from config import ASSETS_DIR

logger = logging.getLogger(__name__)

# 淡入淡出默认时长（毫秒）
FADE_DEFAULT = 1500

# BGM 音频目录
_BGM_DIR = os.path.join(ASSETS_DIR, "audio", "bgm")


class BGMPlayer:
    """
    BGM 播放器。

    用法：
        bgm = BGMPlayer()
        bgm.register_bgm("area_graveyard", "assets/audio/bgm/graveyard.ogg")
        bgm.play("area_graveyard")            # 淡入播放
        bgm.crossfade("area_swamp", 1200)     # 1.2s 交叉淡入淡出

    静默模式：
        无音频文件时（默认状态），play() 不报错、不中断游戏。
        后续放置音频文件后调用 register_bgm() 即可启用。
    """

    def __init__(self):
        # 区域 ID → BGM 文件路径（绝对路径或相对 assets/ 路径）
        self._bgm_map: Dict[str, str] = {}

        # 当前播放的区域 ID
        self._current_area: str = ""

        # 全局音量
        self._volume: float = 0.5
        self._muted: bool = False

        # mixer 初始化状态
        self._initialized: bool = False

        # 淡入淡出标记（防止重叠交叉淡入淡出）
        self._fading: bool = False

    # ----------------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------------

    def initialize(self) -> None:
        """初始化 pygame.mixer.music 模块。"""
        if self._initialized:
            return

        try:
            pygame.mixer.music.set_volume(self._volume)
            self._initialized = True
            logger.info("BGMPlayer: 初始化完成")
        except pygame.error as e:
            logger.warning("BGMPlayer: mixer.music 初始化失败: %s", e)
            self._initialized = False

    # ----------------------------------------------------------------
    # BGM 注册
    # ----------------------------------------------------------------

    def register_bgm(self, area_id: str, filepath: str) -> None:
        """
        注册区域 BGM。

        :param area_id:  区域 ID（与 map/area.py 中 Area.area_id 一致）
        :param filepath: 音频文件路径（支持 .ogg / .mp3 / .wav）
        """
        self._bgm_map[area_id] = filepath
        logger.info("BGMPlayer: 注册区域 '%s' → %s", area_id, filepath)

    def register_from_config(self, config: dict) -> None:
        """
        从字典批量注册。

        config 格式：
            {"area_graveyard": "bgm/graveyard.ogg",
             "area_swamp":     "bgm/swamp.ogg"}
        """
        for area_id, rel_path in config.items():
            full_path = os.path.join(_BGM_DIR, rel_path) if not os.path.isabs(rel_path) else rel_path
            self.register_bgm(area_id, full_path)

    def unregister(self, area_id: str) -> None:
        """移除区域 BGM 注册。"""
        self._bgm_map.pop(area_id, None)

    # ----------------------------------------------------------------
    # 播放控制
    # ----------------------------------------------------------------

    def play(self, area_id: str, fade_ms: int = FADE_DEFAULT) -> None:
        """
        播放指定区域的 BGM（带淡入）。

        :param area_id:  区域 ID
        :param fade_ms:  淡入时长（毫秒）
        """
        if not self._initialized:
            self.initialize()
        if not self._initialized:
            return

        # 同区域已在播放，不重复
        if area_id == self._current_area and pygame.mixer.music.get_busy():
            return

        filepath = self._bgm_map.get(area_id)
        if filepath is None:
            logger.debug("BGMPlayer: 区域 '%s' 无 BGM 文件，静默", area_id)
            self._current_area = area_id
            return

        if not os.path.isfile(filepath):
            logger.debug("BGMPlayer: BGM 文件不存在: %s，静默", filepath)
            self._current_area = area_id
            return

        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.set_volume(0.0 if self._muted else self._volume)
            pygame.mixer.music.play(loops=-1, fade_ms=fade_ms)
            self._current_area = area_id
            self._fading = False
            logger.info("BGMPlayer: 播放区域 '%s' BGM", area_id)
        except pygame.error as e:
            logger.warning("BGMPlayer: 播放 BGM 失败: %s", e)

    def crossfade(self, area_id: str, fade_ms: int = FADE_DEFAULT) -> None:
        """
        交叉淡入淡出切换到新区域的 BGM。

        当前曲目淡出 → 停止 → 新曲目淡入。
        """
        if self._fading:
            # 已在淡出中，跳过
            return

        self._fading = True

        if self._current_area and pygame.mixer.music.get_busy():
            # 先淡出
            try:
                pygame.mixer.music.fadeout(fade_ms // 2)
            except pygame.error:
                pass

        # 延迟切换：利用 pygame 事件，这里简化为直接调用
        # （pygame.mixer.music.fadeout 是非阻塞的，但随后立即 play 可能冲突）
        # 折中方案：用 stop() + 新曲 play(fade_ms)
        self.play(area_id, fade_ms=fade_ms)
        self._fading = False

    def stop(self, fade_ms: int = 1000) -> None:
        """
        停止 BGM（带淡出）。

        :param fade_ms: 淡出时长（毫秒）
        """
        if not self._initialized:
            return
        try:
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()
            self._current_area = ""
            self._fading = False
        except pygame.error:
            pass

    def pause(self) -> None:
        """暂停 BGM。"""
        if self._initialized:
            try:
                pygame.mixer.music.pause()
            except pygame.error:
                pass

    def unpause(self) -> None:
        """恢复 BGM。"""
        if self._initialized:
            try:
                pygame.mixer.music.unpause()
            except pygame.error:
                pass

    # ----------------------------------------------------------------
    # 音量
    # ----------------------------------------------------------------

    def set_volume(self, volume: float) -> None:
        """设置音量 (0.0 ~ 1.0)。"""
        self._volume = max(0.0, min(1.0, volume))
        if self._initialized and not self._muted:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except pygame.error:
                pass

    def get_volume(self) -> float:
        return self._volume

    def mute(self) -> None:
        """静音。"""
        self._muted = True
        if self._initialized:
            try:
                pygame.mixer.music.set_volume(0.0)
            except pygame.error:
                pass

    def unmute(self) -> None:
        """取消静音。"""
        self._muted = False
        if self._initialized:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except pygame.error:
                pass

    @property
    def is_playing(self) -> bool:
        if not self._initialized:
            return False
        try:
            return pygame.mixer.music.get_busy()
        except pygame.error:
            return False

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    @property
    def current_area(self) -> str:
        return self._current_area

    def get_bgm_path(self, area_id: str) -> Optional[str]:
        """查询某区域的 BGM 路径。"""
        return self._bgm_map.get(area_id)

    def __repr__(self) -> str:
        return (f"<BGMPlayer area='{self._current_area}' "
                f"playing={self.is_playing} volume={self._volume:.1f}>")
