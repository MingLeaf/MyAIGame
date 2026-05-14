# =============================================================
# map/world_map.py —— 世界地图管理（区域解锁 / 区域跳转）
# =============================================================

from __future__ import annotations
import os
from typing import Dict, List, Optional, Set

from map.area import Area
from utils import json_loader
from config import DATA_DIR


class WorldMap:
    """
    世界地图管理器。
    - 维护所有区域的解锁状态
    - 按需加载 / 卸载区域
    - 提供当前活动区域引用
    """

    def __init__(self):
        self._areas:    Dict[str, Area] = {}
        self._unlocked: Set[str]        = set()
        self._current_area_id: str      = ""
        self._config: dict              = {}

    # ---- 初始化 ----

    def load_config(self):
        """加载世界总配置文件"""
        path = os.path.join(DATA_DIR, "maps", "world_config.json")
        try:
            self._config = json_loader.load(path)
        except FileNotFoundError:
            self._config = {"areas": [], "start_area": "area_graveyard"}

        # 初始解锁起始区域
        start = self._config.get("start_area", "area_graveyard")
        self._unlocked.add(start)

    # ---- 区域管理 ----

    def get_area(self, area_id: str) -> Area:
        """获取区域（按需加载）"""
        if area_id not in self._areas:
            area = Area(area_id)
            area.load()
            self._areas[area_id] = area
        return self._areas[area_id]

    def enter_area(self, area_id: str) -> Area:
        """进入指定区域，设为当前区域"""
        area = self.get_area(area_id)
        self._current_area_id = area_id
        return area

    def reload_area(self, area_id: str) -> Area:
        """
        强制重载区域内的动态对象（敌人、篝火）并返回。
        用于"重新开始"等需要完整重置的场景。
        """
        if area_id in self._areas:
            self._areas[area_id].reload()
        else:
            area = Area(area_id)
            area.load()
            self._areas[area_id] = area
        self._current_area_id = area_id
        return self._areas[area_id]

    def unlock_area(self, area_id: str):
        self._unlocked.add(area_id)

    def is_unlocked(self, area_id: str) -> bool:
        return area_id in self._unlocked

    def unlock_connected(self, from_area: str):
        """击败该区域 Boss 后解锁下一个区域"""
        for area_def in self._config.get("areas", []):
            if area_def.get("id") == from_area:
                for next_id in area_def.get("unlocks", []):
                    self.unlock_area(next_id)
                break

    # ---- 属性 ----

    @property
    def current_area(self) -> Optional[Area]:
        if self._current_area_id:
            return self._areas.get(self._current_area_id)
        return None

    @property
    def current_area_id(self) -> str:
        return self._current_area_id

    @property
    def start_area_id(self) -> str:
        return self._config.get("start_area", "area_graveyard")

    def get_all_unlocked(self) -> List[str]:
        return list(self._unlocked)


# 全局单例
world_map = WorldMap()
