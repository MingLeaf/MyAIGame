# =============================================================
# systems/__init__.py —— 系统层（独立于实体的全局子系统）
# =============================================================
#
# 第 7 阶段：LootSystem（掉落系统）
# 第 8 阶段：SoulFragmentSystem / RespawnSystem / CampfireSystem
#            ProgressionSystem / UpgradeSystem / QuestSystem
# =============================================================
from systems.loot_system import LootSystem                # noqa: F401
from systems.soul_fragment_system import (
    SoulFragmentSystem, DeathRelic,
)                                                         # noqa: F401
from systems.respawn_system import RespawnSystem          # noqa: F401
from systems.campfire_system import CampfireSystem        # noqa: F401
from systems.progression_system import ProgressionSystem  # noqa: F401
from systems.upgrade_system import UpgradeSystem          # noqa: F401
from systems.quest_system import QuestSystem              # noqa: F401

__all__ = [
    "LootSystem",
    "SoulFragmentSystem",
    "DeathRelic",
    "RespawnSystem",
    "CampfireSystem",
    "ProgressionSystem",
    "UpgradeSystem",
    "QuestSystem",
]
