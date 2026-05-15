# =============================================================
# entities/npc/blacksmith.py —— 铁匠 NPC（武器强化 / 材料购买 / 对话）
# 第 10 阶段：NPC 与对话系统
# =============================================================

from __future__ import annotations
from typing import TYPE_CHECKING

from entities.npc.base_npc import BaseNPC

if TYPE_CHECKING:
    from entities.player.player import Player


class BlacksmithNPC(BaseNPC):
    """
    铁匠。
    提供：武器强化、路线选择。
    位于第二个营地旁（废弃工坊区域）。
    """

    def __init__(self, npc_id: str, x: float, y: float):
        super().__init__(npc_id, x, y,
                         display_name="铁匠 多兰",
                         color=(200, 130, 60))

        self.load_dialogue("npc_blacksmith.json")
        self._player: "Player" = None

    def set_context(self, player, area=None):
        self._player = player

    # ---- 动作回调 ----

    def do_weapon_upgrade(self, data: dict = None):
        """打开武器强化面板。"""
        from core.event_manager import event_manager
        event_manager.emit("npc_open_weapon_upgrade", {"npc": self})

    def do_chat(self, data: dict = None):
        pass

    def get_actions(self) -> dict:
        return {
            "open_weapon_upgrade": self.do_weapon_upgrade,
            "chat":                self.do_chat,
        }
