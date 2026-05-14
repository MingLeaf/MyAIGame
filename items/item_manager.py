# =============================================================
# items/item_manager.py —— 物品生成 / 掉落 / 拾取
#
# 职责：
#   1. 提供 create()/spawn_drop()/roll_and_spawn() 三个入口，
#      与 combat.drop_system 衔接（沿用 DropEntry / roll_drops）。
#   2. DroppedItem：掉落到地图上的可拾取实体
#      - 简易物理：弹跳 + 重力 + 地面碰撞
#      - 玩家进入半径自动拾取（也可由场景按 F 键调用）
#      - 自动过期消失
#   3. 暴露便捷方法 try_pickup_all(player, area)，供 GameScene
#      每帧调用拾取附近所有 DroppedItem。
# =============================================================
from __future__ import annotations

import pygame
from typing import List, Optional, Tuple, TYPE_CHECKING

from core.event_manager import event_manager

if TYPE_CHECKING:
    from items.item_base import Item
    from entities.player.player import Player
    from map.area import Area


# ----------------------------------------------------------------
# DroppedItem —— 地面掉落物
# ----------------------------------------------------------------

class DroppedItem:
    """
    地面掉落物实体。

    生命周期：
        1. spawn_drop 创建 → 加入 area.dropped_items
        2. 每帧 update(dt, collision_map) 处理弹跳 + 重力
        3. 玩家走入半径 → try_pickup(player) → 加入背包 → picked=True
        4. 超过 LIFETIME 秒未被拾取 → expired=True
        5. ItemManager.try_pickup_all 清理 picked/expired 实体
    """

    PICKUP_RADIUS = 36         # 玩家自动拾取半径（像素）
    LIFETIME      = 90.0       # 自动消失时间（秒）

    SIZE_W = 16
    SIZE_H = 16

    GRAVITY    = 1200.0
    INITIAL_VY = -260.0        # 出生时向上小弹

    def __init__(self, item_id: str, quantity: int, x: float, y: float):
        self.item_id   = item_id
        self.quantity  = max(1, int(quantity))
        self.x         = float(x)
        self.y         = float(y)
        self.vy        = float(self.INITIAL_VY)
        self.elapsed   = 0.0
        self.picked    = False
        self.expired   = False
        self.on_ground = False

        # 用于碰撞 / 渲染
        self.rect = pygame.Rect(
            int(self.x) - self.SIZE_W // 2,
            int(self.y) - self.SIZE_H // 2,
            self.SIZE_W, self.SIZE_H,
        )

    # ----------------------------------------------------------------
    # 物理更新
    # ----------------------------------------------------------------

    def update(self, dt: float, collision_map=None) -> None:
        if self.picked or self.expired:
            return
        self.elapsed += dt
        if self.elapsed >= self.LIFETIME:
            self.expired = True
            return

        # 简易重力
        if not self.on_ground:
            self.vy = min(900.0, self.vy + self.GRAVITY * dt)
            new_y = self.y + self.vy * dt

            # 简单地面检测：尝试新位置，若与地面相交则停下
            if collision_map is not None:
                test_rect = pygame.Rect(
                    int(self.x) - self.SIZE_W // 2,
                    int(new_y) - self.SIZE_H // 2,
                    self.SIZE_W, self.SIZE_H,
                )
                if self._is_solid(collision_map, test_rect):
                    # 二分回退到地面（最多 8 步）
                    lo, hi = self.y, new_y
                    for _ in range(8):
                        mid = (lo + hi) * 0.5
                        mid_rect = test_rect.copy()
                        mid_rect.y = int(mid) - self.SIZE_H // 2
                        if self._is_solid(collision_map, mid_rect):
                            hi = mid
                        else:
                            lo = mid
                    self.y = lo
                    self.vy = 0.0
                    self.on_ground = True
                else:
                    self.y = new_y
            else:
                self.y = new_y

        self.rect.x = int(self.x) - self.SIZE_W // 2
        self.rect.y = int(self.y) - self.SIZE_H // 2

    @staticmethod
    def _is_solid(collision_map, rect: pygame.Rect) -> bool:
        """检测 rect 是否与实心瓦片或单向平台相交。"""
        # 优先：CollisionMap.get_solid_tiles_in_rect
        fn = getattr(collision_map, "get_solid_tiles_in_rect", None)
        if fn is not None:
            try:
                if fn(rect):
                    return True
            except Exception:
                pass
        # 单向平台也算地面（让物品落在其上）
        fn_p = getattr(collision_map, "get_platform_tiles_in_rect", None)
        if fn_p is not None:
            try:
                if fn_p(rect):
                    return True
            except Exception:
                pass
        # 兜底：逐点 is_solid_at
        is_solid_at = getattr(collision_map, "is_solid_at", None)
        if is_solid_at is not None:
            for px, py in (rect.bottomleft, rect.bottomright, rect.midbottom):
                try:
                    if is_solid_at(float(px), float(py)):
                        return True
                except Exception:
                    continue
        return False

    # ----------------------------------------------------------------
    # 拾取
    # ----------------------------------------------------------------

    def can_pickup(self, player: "Player") -> bool:
        if self.picked or self.expired:
            return False
        if not hasattr(player, "rect"):
            return False
        dx = player.rect.centerx - (self.rect.x + self.SIZE_W // 2)
        dy = player.rect.centery - (self.rect.y + self.SIZE_H // 2)
        return dx * dx + dy * dy <= self.PICKUP_RADIUS * self.PICKUP_RADIUS

    def try_pickup(self, player: "Player") -> bool:
        """
        尝试被玩家拾取。
        成功后派发 'item_picked_up' 事件。
        """
        if not self.can_pickup(player):
            return False

        from items.item_database import item_db
        item = item_db.create(self.item_id)
        if item is None:
            self.expired = True
            return False

        inv = getattr(player, "inventory", None)
        if inv is None:
            return False

        ok, leftover = inv.add(item, self.quantity)
        actual = self.quantity - leftover
        if not ok or actual <= 0:
            return False

        # 部分拾取：剩余仍留在地上
        self.quantity = leftover
        if leftover <= 0:
            self.picked = True

        event_manager.emit("item_picked_up", {
            "item_id":  self.item_id,
            "quantity": actual,
            "name":     getattr(item, "name", self.item_id),
            "player":   player,
            "world_x":  self.rect.centerx,
            "world_y":  self.rect.top,
        })
        return True

    # ----------------------------------------------------------------
    # 渲染
    # ----------------------------------------------------------------

    def render(self, surface: pygame.Surface, cam_offset: Tuple[int, int]) -> None:
        if self.picked or self.expired:
            return
        ox, oy = cam_offset
        # 简易光晕：根据剩余寿命淡出
        remaining = max(0.0, self.LIFETIME - self.elapsed)
        alpha = 255 if remaining > 5.0 else int(255 * (remaining / 5.0))
        screen_rect = self.rect.move(-ox, -oy)

        # 绘制带边框的方块作为占位图标
        body = pygame.Surface((self.SIZE_W, self.SIZE_H), pygame.SRCALPHA)
        body.fill((255, 220, 80, max(0, min(255, alpha))))
        pygame.draw.rect(body, (100, 70, 20, max(0, min(255, alpha))),
                         (0, 0, self.SIZE_W, self.SIZE_H), 1)
        surface.blit(body, screen_rect.topleft)


# ----------------------------------------------------------------
# ItemManager —— 物品生成 / 掉落 / 拾取入口
# ----------------------------------------------------------------

class ItemManager:
    """物品系统统一入口（无状态，全部 staticmethod）。"""

    # ---- 创建 ----

    @staticmethod
    def create(item_id: str) -> Optional["Item"]:
        """从 item_database 创建物品独立副本。"""
        from items.item_database import item_db
        return item_db.create(item_id)

    # ---- 掉落（生成地面实体） ----

    @staticmethod
    def spawn_drop(area: "Area", x: float, y: float,
                   item_id: str, quantity: int = 1) -> Optional[DroppedItem]:
        """
        在世界坐标 (x, y) 生成一个 DroppedItem。
        会自动 push 到 area.dropped_items。
        """
        if area is None:
            return None
        if not hasattr(area, "dropped_items"):
            # area 兼容性兜底
            area.dropped_items = []   # type: ignore[attr-defined]
        di = DroppedItem(item_id, quantity, x, y)
        area.dropped_items.append(di)
        event_manager.emit("item_dropped_to_world", {
            "item_id":  item_id,
            "quantity": quantity,
            "world_x":  int(x),
            "world_y":  int(y),
        })
        return di

    @staticmethod
    def roll_and_spawn(area: "Area", x: float, y: float,
                       drop_table) -> List[DroppedItem]:
        """
        对 drop_table（list[DropEntry]）掷骰，将命中物品生成到世界中。
        :return: 已生成的 DroppedItem 列表（顺序 = 掷骰顺序）。
        """
        from combat.drop_system import roll_drops
        results = roll_drops(drop_table)
        out: List[DroppedItem] = []
        # 多个物品略错开 X，避免完全重叠
        offset = -((len(results) - 1) * 8) // 2 if results else 0
        for i, (item_id, qty) in enumerate(results):
            di = ItemManager.spawn_drop(area, x + offset + i * 8, y, item_id, qty)
            if di is not None:
                out.append(di)
        return out

    # ---- 拾取 ----

    @staticmethod
    def try_pickup_all(player: "Player", area: "Area") -> List[DroppedItem]:
        """
        遍历 area.dropped_items，对范围内的全部尝试拾取。
        :return: 实际成功拾取的 DroppedItem 列表（用于上层飘字）。
        """
        if area is None or not hasattr(area, "dropped_items"):
            return []
        picked: List[DroppedItem] = []
        for di in list(area.dropped_items):
            if di.try_pickup(player):
                picked.append(di)
        # 清理已 picked / expired
        area.dropped_items = [
            d for d in area.dropped_items
            if not (d.picked or d.expired)
        ]
        return picked

    @staticmethod
    def update_drops(area: "Area", dt: float) -> None:
        """每帧更新所有掉落物物理 + 生命周期。"""
        if area is None or not hasattr(area, "dropped_items"):
            return
        col = getattr(area, "collision", None)
        for di in area.dropped_items:
            di.update(dt, col)
        # 清理过期
        area.dropped_items = [
            d for d in area.dropped_items if not d.expired
        ]


__all__ = ["DroppedItem", "ItemManager"]
