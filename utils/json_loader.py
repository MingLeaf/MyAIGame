# =============================================================
# utils/json_loader.py —— JSON 数据加载器（带缓存）
# =============================================================

import json
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# 全局文件级缓存
_cache: Dict[str, dict] = {}


def load(path: str, use_cache: bool = True) -> dict:
    """
    加载 JSON 文件并返回解析后的字典/列表。

    :param path:      文件绝对路径
    :param use_cache: 是否使用缓存（同一路径只读一次）
    :raises FileNotFoundError: 文件不存在
    :raises json.JSONDecodeError: JSON 格式错误
    """
    abs_path = os.path.abspath(path)

    if use_cache and abs_path in _cache:
        return _cache[abs_path]

    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"JSONLoader: 找不到文件 '{abs_path}'")

    with open(abs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if use_cache:
        _cache[abs_path] = data

    logger.debug("JSONLoader: 已加载 '%s'", abs_path)
    return data


def load_from_data_dir(relative_path: str, use_cache: bool = True) -> dict:
    """
    相对于项目 data/ 目录加载 JSON。

    :param relative_path: 相对于 data/ 的路径，例如 "entities/player_base_stats.json"
    """
    from config import DATA_DIR
    full_path = os.path.join(DATA_DIR, relative_path)
    return load(full_path, use_cache)


def clear_cache():
    """清除全部缓存（测试 / 热重载使用）"""
    _cache.clear()


def reload(path: str) -> dict:
    """强制重新加载文件（忽略缓存）"""
    return load(path, use_cache=False)
