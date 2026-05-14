# =============================================================
# systems/__init__.py —— 系统层（独立于实体的全局子系统）
# =============================================================
#
# 第 7 阶段创建。后续阶段（第 8 阶段·游戏规则核心）会陆续加入：
#   - soul_fragment_system / respawn_system / campfire_system
#   - progression_system / upgrade_system / quest_system
# =============================================================
from systems.loot_system import LootSystem  # noqa: F401

__all__ = ["LootSystem"]
