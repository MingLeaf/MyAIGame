# =============================================================
# physics/movement_resolver.py —— 移动解算器（位移 + 碰撞响应）
# =============================================================

from __future__ import annotations
from typing import Tuple, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from map.collision_map import CollisionMap


class MovementResolver:
    """
    轴分离平台游戏移动解算器。

    执行顺序：先 X 轴，再 Y 轴，分别独立处理碰撞，避免卡角。

    碰撞方向判断（实体中心 vs 瓦片中心）：
      X 轴：实体中心偏左 → 推出到左（right=tile.left）
             实体中心偏右 → 推出到右（left=tile.right）
      Y 轴：实体中心偏上 → 推出到上（bottom=tile.top）→ 落地
             实体中心偏下 → 推出到下（top=tile.bottom） → 撞顶

    单向平台额外规则：
      - 仅当实体**移动前**的底部 <= 平台顶部时才产生碰撞（即从上方进入）
      - pass_through_platform=True 时完全跳过平台碰撞
    """

    def resolve(self,
                rect: pygame.Rect,
                vel_x: float,
                vel_y: float,
                dt: float,
                collision_map: "CollisionMap",
                pass_through_platform: bool = False,
                ) -> Tuple[pygame.Rect, bool, float, float]:
        """
        执行一帧的移动解算。

        :param rect:                  实体当前碰撞矩形（世界坐标）
        :param vel_x:                 X 速度（像素/秒）
        :param vel_y:                 Y 速度（像素/秒）
        :param dt:                    帧时间（秒）
        :param collision_map:         碰撞地图引用
        :param pass_through_platform: 为 True 时跳过单向平台碰撞（S+跳）
        :return: (new_rect, on_ground, new_vel_x, new_vel_y)
        """
        # 记录本帧移动前的原始矩形（用于平台"来自上方"判断）
        orig_rect = rect.copy()
        new_rect  = rect.copy()
        on_ground = False

        # ============================================================
        # 第一步：X 轴移动 + 水平碰撞
        # ============================================================
        move_x = int(vel_x * dt)
        if move_x != 0:
            new_rect.x += move_x
            for tile_rect in collision_map.get_solid_tiles_in_rect(new_rect):
                if not new_rect.colliderect(tile_rect):
                    continue
                # 用中心相对位置判断推出方向
                if new_rect.centerx <= tile_rect.centerx:
                    new_rect.right = tile_rect.left   # 从左侧进入，推到左边
                else:
                    new_rect.left = tile_rect.right   # 从右侧进入，推到右边
                vel_x = 0.0

        # ============================================================
        # 第二步：Y 轴移动 + 垂直碰撞
        # ============================================================
        move_y = int(vel_y * dt)
        new_rect.y += move_y

        for tile_rect in collision_map.get_solid_tiles_in_rect(new_rect):
            if not new_rect.colliderect(tile_rect):
                continue
            if new_rect.centery <= tile_rect.centery:
                # 实体中心在瓦片中心上方 → 从上方进入 → 落地
                new_rect.bottom = tile_rect.top
                on_ground = True
                vel_y = 0.0
            else:
                # 实体中心在瓦片中心下方 → 从下方进入 → 撞顶
                new_rect.top = tile_rect.bottom
                if vel_y < 0:
                    vel_y = 0.0

        # ---- 地面探针：防止 vel_y=0 时因无位移而检测不到地面 ----
        # 向下探测 2px，若正下方有实心瓦片则视为站在地面上
        if not on_ground and vel_y >= 0:
            probe = pygame.Rect(
                new_rect.left + 2,
                new_rect.bottom,
                max(1, new_rect.width - 4),
                2,
            )
            for tile_rect in collision_map.get_solid_tiles_in_rect(probe):
                if probe.colliderect(tile_rect):
                    on_ground = True
                    vel_y = 0.0
                    break

        # ============================================================
        # 第三步：单向平台碰撞
        # ============================================================
        # 条件：未请求穿透 且 当前速度向下（或为零，站立维持）
        if not pass_through_platform and vel_y >= 0:
            # 用略微扩展的检测矩形（底部多 2px），确保"恰好贴着"也能被检测到
            detect = pygame.Rect(
                new_rect.left + 1,
                new_rect.top,
                max(1, new_rect.width - 2),
                new_rect.height + 2,
            )
            for tile_rect in collision_map.get_platform_tiles_in_rect(detect):
                # 判断"来自上方"：移动前底部 <= 平台顶部（含 4px 容差）
                from_above = orig_rect.bottom <= tile_rect.top + 4
                # 判断"已到达或越过"：移动后底部 >= 平台顶部
                reached    = new_rect.bottom >= tile_rect.top
                if from_above and reached:
                    new_rect.bottom = tile_rect.top
                    on_ground = True
                    vel_y = 0.0

        return new_rect, on_ground, vel_x, vel_y
