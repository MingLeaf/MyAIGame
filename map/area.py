# =============================================================
# map/area.py —— 单个区域类（含瓦片地图 / 实体列表 / 营地位置）
# =============================================================

from __future__ import annotations
import os
from typing import List, Optional, Dict, Any
import pygame

from map.tile_map     import TileMap
from map.collision_map import CollisionMap
from map.layer_renderer import LayerRenderer
from map.campfire      import Campfire
from map.trap          import Trap
from map.transition_gate import TransitionGate
from utils import json_loader
from config import DATA_DIR

# 延迟导入，避免循环引用
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from entities.enemy.base_enemy import BaseEnemy


class Area:
    """
    游戏中的一个区域（关卡）。
    负责：
    - 加载该区域的地图和对象数据
    - 管理区域内的营地、陷阱、传送门
    - 向上层提供渲染和碰撞访问
    """

    def __init__(self, area_id: str):
        self.area_id   = area_id
        self.tile_map  = TileMap()
        self.collision : Optional[CollisionMap] = None
        self.layer_renderer: Optional[LayerRenderer] = None

        self.campfires:   List[Campfire] = []
        self.traps:       List[Trap]     = []
        self.transitions: List[TransitionGate] = []
        self.enemies:     List["BaseEnemy"] = []
        # 第 5 阶段·武器系统：抛射物列表（弓箭 / 魔法弹）
        # GameScene 每帧需调用 update() 推进；命中检测由 HitResolver 处理
        self.projectiles: List = []
        # 第 6 阶段·物品系统：地面掉落物列表
        # 由 ItemManager.spawn_drop() / roll_and_spawn() 写入，
        # GameScene 通过 ItemManager.update_drops + try_pickup_all 驱动
        self.dropped_items: List = []

        self._loaded = False

    # ---- 加载 ----

    def load(self):
        """从 data/maps/{area_id}/ 加载地图和对象数据"""
        map_dir  = os.path.join(DATA_DIR, "maps", self.area_id)
        map_path = os.path.join(map_dir, "tilemap.json")

        self.tile_map.load(map_path)
        self.collision      = CollisionMap(self.tile_map)
        self.layer_renderer = LayerRenderer(self.tile_map)

        # 加载营地
        self.campfires.clear()
        for cf_data in self.tile_map.objects.get("campfires", []):
            ts = self.tile_map.tile_size
            cf = Campfire(
                campfire_id = cf_data.get("id", f"cf_{len(self.campfires)}"),
                world_x     = cf_data.get("x", 0) * ts + ts // 2,
                world_y     = cf_data.get("y", 0) * ts,
            )
            self.campfires.append(cf)

        # 加载传送门
        self.transitions.clear()
        for gate_data in self.tile_map.objects.get("transitions", []):
            ts = self.tile_map.tile_size
            rect = pygame.Rect(
                gate_data.get("x", 0) * ts,
                gate_data.get("y", 0) * ts,
                gate_data.get("w", 2) * ts,
                gate_data.get("h", 3) * ts,
            )
            gate = TransitionGate(
                rect         = rect,
                target_area  = gate_data.get("target_area", ""),
                target_spawn = gate_data.get("target_spawn", "default"),
                direction    = gate_data.get("direction", "right"),
            )
            self.transitions.append(gate)

        # 加载敌人
        self._load_enemies()

        self._loaded = True

    def reload(self):
        """
        完整重置区域内的所有动态对象（敌人、篝火），
        供"重新开始"等需要完全重置游戏状态的场景使用。
        地图瓦片/碰撞数据不变，仅重建实体。
        """
        # 重置篝火激活状态（重新实例化）
        campfire_data = self.tile_map.objects.get("campfires", [])
        self.campfires.clear()
        ts = self.tile_map.tile_size
        for cf_data in campfire_data:
            cf = Campfire(
                campfire_id = cf_data.get("id", f"cf_{len(self.campfires)}"),
                world_x     = cf_data.get("x", 0) * ts + ts // 2,
                world_y     = cf_data.get("y", 0) * ts,
            )
            self.campfires.append(cf)

        # 清空抛射物 / 掉落物（重置场景状态）
        self.projectiles.clear()
        self.dropped_items.clear()

        # 重载敌人（全部重新生成）
        self._load_enemies()

    def _load_enemies(self):
        """
        加载敌人实例。
        第 7 阶段：优先通过 enemy_spawner 读取
        data/maps/<area_id>/enemy_spawns.json，缺失则回退到 tilemap 内嵌的
        enemy_spawns 字段。
        """
        from entities.enemy.enemy_spawner import spawn_from_area_file

        self.enemies.clear()
        spawn_from_area_file(self, self.area_id)

    # ---- 更新 ----

    def update(self, dt: float, player_rect: pygame.Rect):
        for cf in self.campfires:
            cf.update(dt, player_rect)
        for trap in self.traps:
            trap.update(dt)

    # ---- 渲染 ----

    def render_background(self, renderer, camera):
        if self.layer_renderer:
            self.layer_renderer.render(renderer, camera)

    def render_objects(self, surface: pygame.Surface, cam_offset: tuple):
        """渲染区域内的营地、陷阱、地面掉落物等对象"""
        for cf in self.campfires:
            cf.render(surface, cam_offset)
        # 地面掉落物（第 6 阶段）
        for di in self.dropped_items:
            di.render(surface, cam_offset)

    def render_foreground(self, renderer, camera):
        if self.layer_renderer:
            self.layer_renderer.render_foreground(renderer, camera)

    # ---- 属性 ----

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def world_bounds(self) -> pygame.Rect:
        return pygame.Rect(0, 0,
                           self.tile_map.world_width,
                           self.tile_map.world_height)

    def get_spawn_point(self, spawn_id: str = "default") -> tuple:
        return self.tile_map.get_spawn_point()
