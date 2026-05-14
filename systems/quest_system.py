# =============================================================
# systems/quest_system.py —— 游戏进度系统
#
# 第 8 阶段：追踪 Boss 击杀记录、区域解锁状态、游戏完成度。
#
# 设计：
#   - 无状态单例，所有数据通过静态方法访问
#   - Boss 击杀记录写入内存 + 事件总线广播
#   - 区域解锁状态与 world_map 联动
#
# 使用：
#   from systems.quest_system import QuestSystem
#   QuestSystem.record_boss_kill("duke_rotbone")
#   QuestSystem.is_boss_killed("duke_rotbone")  → bool
#   QuestSystem.progress_summary()              → dict
# =============================================================
from __future__ import annotations
from typing import Set, List, Dict


class QuestSystem:
    """
    进度追踪器（全静态方法，无实例化需求）。

    追踪项目：
      - killed_bosses: set[str]  已击杀 Boss ID 集合
      - unlocked_areas: set[str]  已解锁区域 ID 集合
      - campfires_activated: set[str]  已激活营地 ID 集合
    """

    _killed_bosses: Set[str] = set()
    _unlocked_areas: Set[str] = set()
    _campfires_activated: Set[str] = set()
    _initialized: bool = False

    # ----------------------------------------------------------------
    # 初始化
    # ----------------------------------------------------------------

    @classmethod
    def init(cls) -> None:
        """首次调用时初始化（从 world_config 读取起始区域）。"""
        if cls._initialized:
            return
        cls._initialized = True
        try:
            from map.world_map import world_map
            cls._unlocked_areas.add(world_map.start_area_id)
        except Exception:
            cls._unlocked_areas.add("area_graveyard")

    @classmethod
    def hard_reset(cls) -> None:
        """完全重置所有进度（新游戏开始）。"""
        cls._killed_bosses.clear()
        cls._unlocked_areas.clear()
        cls._campfires_activated.clear()
        cls._initialized = False
        cls.init()

    # ----------------------------------------------------------------
    # Boss 击杀
    # ----------------------------------------------------------------

    @classmethod
    def record_boss_kill(cls, boss_id: str) -> None:
        """记录一个 Boss 已被击杀。"""
        cls.init()
        if boss_id not in cls._killed_bosses:
            cls._killed_bosses.add(boss_id)
            from core.event_manager import event_manager
            event_manager.emit("boss_killed", {"boss_id": boss_id})

            # 自动解锁下一区域
            cls._unlock_next_areas(boss_id)

    @classmethod
    def is_boss_killed(cls, boss_id: str) -> bool:
        """查询 Boss 是否已被击杀。"""
        return boss_id in cls._killed_bosses

    @classmethod
    def killed_bosses(cls) -> Set[str]:
        """返回已击杀 Boss 集合的副本。"""
        return set(cls._killed_bosses)

    # ----------------------------------------------------------------
    # 区域解锁
    # ----------------------------------------------------------------

    @classmethod
    def unlock_area(cls, area_id: str) -> None:
        """手动解锁一个区域。"""
        cls.init()
        if area_id not in cls._unlocked_areas:
            cls._unlocked_areas.add(area_id)
            from core.event_manager import event_manager
            event_manager.emit("area_unlocked", {"area_id": area_id})
            # 同步到 world_map
            try:
                from map.world_map import world_map
                world_map.unlock_area(area_id)
            except Exception:
                pass

    @classmethod
    def is_area_unlocked(cls, area_id: str) -> bool:
        """查询区域是否已解锁。"""
        cls.init()
        return area_id in cls._unlocked_areas

    @classmethod
    def unlocked_areas(cls) -> Set[str]:
        """返回已解锁区域集合的副本。"""
        cls.init()
        return set(cls._unlocked_areas)

    @classmethod
    def _unlock_next_areas(cls, boss_id: str) -> None:
        """根据 world_config 自动解锁下一个区域。"""
        try:
            from map.world_map import world_map
            # 反向查找：哪个区域有这个 Boss
            for area_def in world_map._config.get("areas", []):
                if area_def.get("boss") == boss_id:
                    for next_id in area_def.get("unlocks", []):
                        cls.unlock_area(next_id)
                    break
        except Exception:
            pass

    # ----------------------------------------------------------------
    # 营地追踪
    # ----------------------------------------------------------------

    @classmethod
    def record_campfire(cls, campfire_id: str) -> None:
        """记录营地已被激活。"""
        cls._campfires_activated.add(campfire_id)

    @classmethod
    def is_campfire_activated(cls, campfire_id: str) -> bool:
        return campfire_id in cls._campfires_activated

    @classmethod
    def activated_campfires(cls) -> Set[str]:
        return set(cls._campfires_activated)

    # ----------------------------------------------------------------
    # 进度汇总
    # ----------------------------------------------------------------

    @classmethod
    def progress_summary(cls) -> Dict:
        """返回当前进度摘要（供存档/UI 使用）。"""
        cls.init()
        return {
            "killed_bosses":     list(cls._killed_bosses),
            "unlocked_areas":    list(cls._unlocked_areas),
            "activated_campfires": list(cls._campfires_activated),
        }

    @classmethod
    def load_progress(cls, data: Dict) -> None:
        """从存档数据恢复进度。"""
        cls._killed_bosses = set(data.get("killed_bosses", []))
        cls._unlocked_areas = set(data.get("unlocked_areas", []))
        cls._campfires_activated = set(data.get("activated_campfires", []))
        cls._initialized = True


__all__ = ["QuestSystem"]
