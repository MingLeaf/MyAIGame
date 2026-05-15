# =============================================================
# entities/npc/merchant.py —— 商人 NPC（消耗品买卖 / 对话）
# 第 10 阶段：NPC 与对话系统
# =============================================================

from __future__ import annotations
from typing import TYPE_CHECKING

from entities.npc.base_npc import BaseNPC

if TYPE_CHECKING:
    from entities.player.player import Player


class MerchantNPC(BaseNPC):
    """
    旅行商人。
    提供：消耗品购买、物品出售（未来）。
    位于第三个营地旁（出口走廊区域）。
    """

    def __init__(self, npc_id: str, x: float, y: float):
        super().__init__(npc_id, x, y,
                         display_name="商人 莉亚",
                         color=(200, 180, 60))

        self.load_dialogue("npc_merchant.json")
        self._player: "Player" = None

    def set_context(self, player, area=None):
        self._player = player

    # ---- 动作回调 ----

    def do_buy_items(self, data: dict = None):
        """打开购买界面（目前暂用事件通知，后续可实现完整商店 UI）。"""
        from core.event_manager import event_manager
        event_manager.emit("npc_open_shop", {"npc": self})

    def do_chat(self, data: dict = None):
        pass

    def get_actions(self) -> dict:
        return {
            "open_shop": self.do_buy_items,
            "chat":      self.do_chat,
        }
