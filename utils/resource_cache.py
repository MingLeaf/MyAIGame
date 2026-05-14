# =============================================================
# utils/resource_cache.py —— 资源缓存池（图片 / 音频）
# =============================================================

import os
import logging
from typing import Dict, Optional

import pygame

logger = logging.getLogger(__name__)

# 图片缓存 {abs_path: pygame.Surface}
_image_cache: Dict[str, pygame.Surface] = {}

# 音效缓存 {abs_path: pygame.mixer.Sound}
_sound_cache: Dict[str, "pygame.mixer.Sound"] = {}


# -------------------------------------------------------
# 图片
# -------------------------------------------------------

def load_image(path: str,
               convert_alpha: bool = True,
               use_cache: bool = True) -> pygame.Surface:
    """
    加载图片并返回 Surface。

    :param path:          文件绝对路径
    :param convert_alpha: 是否调用 convert_alpha()（含透明通道时应为 True）
    :param use_cache:     是否使用缓存
    """
    abs_path = os.path.abspath(path)

    if use_cache and abs_path in _image_cache:
        return _image_cache[abs_path]

    if not os.path.isfile(abs_path):
        logger.warning("ResourceCache: 图片文件不存在 '%s'，使用占位图", abs_path)
        return _make_placeholder_image()

    surface = pygame.image.load(abs_path)
    surface = surface.convert_alpha() if convert_alpha else surface.convert()

    if use_cache:
        _image_cache[abs_path] = surface

    logger.debug("ResourceCache: 已加载图片 '%s'", abs_path)
    return surface


def load_image_from_assets(relative_path: str,
                           convert_alpha: bool = True,
                           use_cache: bool = True) -> pygame.Surface:
    """
    相对于 assets/ 目录加载图片。
    """
    from config import ASSETS_DIR
    full_path = os.path.join(ASSETS_DIR, relative_path)
    return load_image(full_path, convert_alpha, use_cache)


def _make_placeholder_image(size=(32, 32),
                             color=(255, 0, 255)) -> pygame.Surface:
    """生成品红色占位图，用于资源缺失时的替代"""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(color)
    return surf


# -------------------------------------------------------
# 音效
# -------------------------------------------------------

def load_sound(path: str, use_cache: bool = True) -> Optional["pygame.mixer.Sound"]:
    """
    加载音效文件，返回 Sound 对象。
    若 mixer 未初始化或文件不存在则返回 None。
    """
    if not pygame.mixer.get_init():
        return None

    abs_path = os.path.abspath(path)

    if use_cache and abs_path in _sound_cache:
        return _sound_cache[abs_path]

    if not os.path.isfile(abs_path):
        logger.warning("ResourceCache: 音效文件不存在 '%s'", abs_path)
        return None

    sound = pygame.mixer.Sound(abs_path)

    if use_cache:
        _sound_cache[abs_path] = sound

    logger.debug("ResourceCache: 已加载音效 '%s'", abs_path)
    return sound


# -------------------------------------------------------
# 缓存管理
# -------------------------------------------------------

def clear_image_cache():
    _image_cache.clear()


def clear_sound_cache():
    _sound_cache.clear()


def clear_all():
    _image_cache.clear()
    _sound_cache.clear()


def image_cache_size() -> int:
    return len(_image_cache)


def sound_cache_size() -> int:
    return len(_sound_cache)
