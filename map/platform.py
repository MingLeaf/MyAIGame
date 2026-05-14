# =============================================================
# map/platform.py —— 单向跳跃平台逻辑
# =============================================================

from __future__ import annotations
import pygame


class Platform:
    """
    单向跳跃平台对象。
    规则：
    - 实体从上方落下时阻挡（底部碰顶部）
    - 实体从下方向上时可以穿过
    - 持续按 下键 时可以下落穿过
    """

    def __init__(self, rect: pygame.Rect):
        self.rect = rect

    def should_collide(self,
                       entity_rect: pygame.Rect,
                       entity_vel_y: float,
                       pass_through: bool = False) -> bool:
        """
        判断实体是否应与此平台发生碰撞（仅顶面）。

        :param entity_rect:   实体当前位置矩形
        :param entity_vel_y:  实体 Y 速度（正值 = 向下）
        :param pass_through:  玩家是否按下"下穿"键
        :return: True = 应碰撞（落地）
        """
        if pass_through:
            return False
        if entity_vel_y < 0:
            # 向上运动时不碰撞
            return False
        # 实体前一帧底部必须在平台顶部或以上才算是"落下"
        # 这里简化：只要实体底部接近平台顶部且向下移动即碰撞
        return True

    def resolve(self, entity_rect: pygame.Rect) -> pygame.Rect:
        """
        将实体对齐到平台顶部（修正 Y 轴）。
        返回修正后的矩形（不修改原矩形）。
        """
        return entity_rect.move(0, self.rect.top - entity_rect.bottom)
