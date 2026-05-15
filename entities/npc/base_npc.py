# =============================================================
# entities/npc/base_npc.py —— NPC 基类（交互范围 / 对话触发 / 头顶提示符）
# 第 10 阶段：NPC 与对话系统
# =============================================================

from __future__ import annotations
import pygame
from typing import Optional, Tuple, Callable, Dict, Any

from entities.base_entity import BaseEntity
from utils.color import WHITE, UI_HIGHLIGHT, COLOR_HP
from ui.font_manager import get_font


class BaseNPC(BaseEntity):
    """
    NPC 基类 —— 非战斗交互角色。

    属性：
    - 交互半径（INTERACT_RADIUS）：玩家进入此范围时显示提示
    - 头顶名称标签
    - 对话触发回调
    """

    INTERACT_RADIUS = 56  # 交互触发半径（像素）

    NPC_WIDTH  = 28
    NPC_HEIGHT = 48

    def __init__(self, npc_id: str, x: float, y: float,
                 display_name: str = "NPC",
                 color: Tuple[int, int, int] = (100, 180, 220)):
        super().__init__(x, y, self.NPC_WIDTH, self.NPC_HEIGHT)
        self.team = "player"  # NPC 属于玩家阵营
        self.npc_id = npc_id
        self.display_name = display_name
        self.color = color
        self._near_player: bool = False

        # 交互区域（圆形检测用矩形近似）
        r = self.INTERACT_RADIUS
        self.interact_rect = pygame.Rect(
            int(self.x) - r, int(self.y) - r * 2, r * 2, r * 2
        )

        # 对话数据（由子类在 __init__ 中通过 load_dialogue 加载）
        self._dialogue_data: Optional[Dict[str, Any]] = None
        # 动作回调表：{"action_name": callable}
        self._actions: Dict[str, Callable] = {}

    # ---- 更新 ----

    def update(self, dt: float, player_rect: pygame.Rect):
        """每帧更新：检测玩家是否在交互范围内。"""
        self._near_player = self.interact_rect.colliderect(player_rect)

    # ---- 交互 ----

    def is_near(self) -> bool:
        """玩家是否在交互范围内。"""
        return self._near_player

    def get_dialogue(self) -> Optional[Dict[str, Any]]:
        """返回此 NPC 的对话树数据。"""
        return self._dialogue_data

    def get_action(self, action_name: str) -> Optional[Callable]:
        """获取指定名称的动作回调。"""
        return self._actions.get(action_name)

    def register_action(self, name: str, callback: Callable):
        """注册一个对话选项动作。"""
        self._actions[name] = callback

    def load_dialogue(self, filename: str):
        """从 data/dialogues/{filename} 加载对话树 JSON。"""
        from utils.json_loader import load_from_data_dir
        try:
            self._dialogue_data = load_from_data_dir(f"dialogues/{filename}")
        except Exception:
            self._dialogue_data = None

    # ---- 渲染 ----

    def render(self, surface: pygame.Surface, cam_offset: Tuple[int, int]):
        ox, oy = cam_offset
        sx = int(self.x) - ox
        sy = int(self.y) - oy

        # 身体
        body_rect = pygame.Rect(sx - 12, sy - 40, 24, 40)
        pygame.draw.rect(surface, self.color, body_rect)
        pygame.draw.rect(surface, (40, 40, 50), body_rect, 2)

        # 头部
        head_center = (sx, sy - 48)
        pygame.draw.circle(surface, self.color, head_center, 10)
        pygame.draw.circle(surface, (40, 40, 50), head_center, 10, 2)

        # 头顶名称标签
        name_font = get_font(14)
        name_surf = name_font.render(self.display_name, True, WHITE)
        surface.blit(name_surf, name_surf.get_rect(center=(sx, sy - 62)))

        # 交互提示（玩家靠近时）
        if self._near_player:
            hint_font = get_font(20)
            hint = hint_font.render(f"[F] 对话", True, UI_HIGHLIGHT)
            surface.blit(hint, hint.get_rect(center=(sx, sy - 78)))


# ---- 工厂函数 ----

def create_npc(npc_type: str, npc_id: str, x: float, y: float) -> BaseNPC:
    """
    根据类型字符串创建 NPC 实例。

    支持的 npc_type:
        "keeper"     → 营地守护者
        "blacksmith" → 铁匠
        "merchant"   → 商人
    """
    from entities.npc import _NPC_REGISTRY

    cls = _NPC_REGISTRY.get(npc_type)
    if cls is None:
        # 回退到基类（占位 NPC）
        return BaseNPC(npc_id, x, y, display_name=f"未知NPC({npc_type})",
                       color=(150, 150, 150))
    return cls(npc_id, x, y)
