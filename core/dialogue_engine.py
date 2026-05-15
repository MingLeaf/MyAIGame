# =============================================================
# core/dialogue_engine.py —— 对话引擎（解析 JSON 对话树 / 节点切换 / 回调动作）
# 第 10 阶段：NPC 与对话系统
# =============================================================

from __future__ import annotations
from typing import Optional, Dict, Any, List, Callable
import logging

_log = logging.getLogger("dialogue")


class DialogueEngine:
    """
    对话引擎：解析 JSON 格式的对话树，驱动对话流程。

    JSON 格式：
    {
      "start_node": "greeting",
      "nodes": {
        "greeting": {
          "text": "流浪者，欢迎来到烬土...",
          "choices": [
            {"text": "我想升级", "action": "open_level_up", "next": null},
            {"text": "我要传送", "action": "open_teleport", "next": null},
            {"text": "只是路过", "action": null, "next": null}
          ]
        }
      }
    }

    用法：
        engine = DialogueEngine(npc_dialogue_data, action_registry)
        engine.start()                    # 进入起始节点
        current_text = engine.current_text   # 当前节点文本
        choices = engine.current_choices     # 当前选项列表
        engine.select_choice(0)              # 选择第 0 项 → 触发 action → 跳转到 next
        engine.is_active                     # 对话是否还在进行
    """

    def __init__(self, dialogue_data: Optional[Dict[str, Any]],
                 action_registry: Optional[Dict[str, Callable]] = None):
        """
        :param dialogue_data:  JSON 格式的对话树
        :param action_registry:  { action_name: callback(data) }，用于执行选项动作
        """
        self._data = dialogue_data or {}
        self._actions = action_registry or {}
        self._current_node_id: Optional[str] = None
        self._current_node: Optional[Dict[str, Any]] = None
        self.is_active: bool = False

    # ---- 控制 ----

    def start(self) -> bool:
        """进入起始节点。返回 True 表示成功。"""
        start_id = self._data.get("start_node")
        if not start_id:
            self.is_active = False
            return False
        return self._goto_node(start_id)

    def select_choice(self, index: int) -> Optional[str]:
        """
        选择一个选项。返回执行的 action_name（若有），无则返回 None。
        对话结束（next 为 null）时 is_active 变为 False。
        """
        if not self._current_node:
            return None

        choices = self._current_node.get("choices", [])
        if index < 0 or index >= len(choices):
            return None

        choice = choices[index]
        action_name = choice.get("action")

        # 执行动作
        if action_name and action_name in self._actions:
            _log.info("ACTION name=%s node=%s", action_name, self._current_node_id)
            try:
                self._actions[action_name]({"choice": choice, "index": index})
            except Exception:
                import traceback
                _log.error("ACTION FAILED name=%s:\n%s", action_name, traceback.format_exc())
                traceback.print_exc()

        # 跳转到下一节点
        next_node = choice.get("next")
        if next_node:
            self._goto_node(next_node)
        else:
            # 对话结束
            self._current_node = None
            self._current_node_id = None
            self.is_active = False

        return action_name

    def _goto_node(self, node_id: str) -> bool:
        nodes = self._data.get("nodes", {})
        node = nodes.get(node_id)
        if node:
            self._current_node_id = node_id
            self._current_node = node
            self.is_active = True
            return True
        self.is_active = False
        return False

    # ---- 查询 ----

    @property
    def current_text(self) -> str:
        """当前节点对话文本。"""
        return self._current_node.get("text", "") if self._current_node else ""

    @property
    def current_choices(self) -> List[Dict[str, Any]]:
        """当前节点选项列表 [{"text":..., "action":..., "next":...}]。"""
        return self._current_node.get("choices", []) if self._current_node else []

    @property
    def speaker_name(self) -> str:
        """当前对话说话者名称。"""
        return self._current_node.get("speaker", "") if self._current_node else ""

    @property
    def node_id(self) -> Optional[str]:
        return self._current_node_id

    def close(self):
        """强制关闭对话。"""
        self._current_node = None
        self._current_node_id = None
        self.is_active = False
