# =============================================================
# entities/npc/keeper.py —— 营地守护者 NPC（升级 / 传送 / 剧情对话）
# 第 10 阶段：NPC 与对话系统
# =============================================================

from __future__ import annotations
from typing import TYPE_CHECKING

from entities.npc.base_npc import BaseNPC

if TYPE_CHECKING:
    from entities.player.player import Player
    from map.area import Area


class KeeperNPC(BaseNPC):
    """
    营地守护者。
    提供：升级（属性分配）、传送（到其他已激活营地）、闲聊。
    位于第一个营地旁，是所有玩家最早接触的 NPC。
    """

    def __init__(self, npc_id: str, x: float, y: float):
        super().__init__(npc_id, x, y,
                         display_name="守护者 艾德",
                         color=(80, 160, 220))

        # 加载对话树
        self.load_dialogue("npc_keeper.json")

        # 注册动作回调（玩家引用由 GameScene 在对话开始前注入）
        self._player: "Player" = None
        self._area: "Area" = None

    def set_context(self, player, area):
        """GameScene 调用：注入玩家和区域引用。"""
        self._player = player
        self._area = area

    # ---- 动作回调（由 DialogueEngine 通过 action_registry 调用）----

    def do_level_up(self, data: dict = None):
        """打开升级面板（复用 CampfireMenu 的升级子面板）。"""
        from core.event_manager import event_manager
        event_manager.emit("npc_open_level_up", {"npc": self})

    def do_teleport(self, data: dict = None):
        """打开传送列表。"""
        from core.event_manager import event_manager
        event_manager.emit("npc_open_teleport", {"npc": self})

    def do_chat(self, data: dict = None):
        """闲聊 —— 只触发对话树下一节点。"""
        pass  # 对话引擎自动跳转到 next node

    def get_actions(self) -> dict:
        """返回动作回调字典，供 DialogueEngine 使用。"""
        return {
            "open_level_up": self.do_level_up,
            "open_teleport": self.do_teleport,
            "chat":          self.do_chat,
        }
