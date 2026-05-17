# =============================================================
# animation/particle_system.py —— 粒子系统
#
# 核心组件：
#   Particle          —— 单个粒子（支持几何图形 / 纹理替换）
#   ParticleEmitter   —— 粒子发射器（管理一组粒子 + 生成参数）
#   PresetEmitters    —— 预设发射器工厂（血溅/火焰/魔法/灰尘/闪光等）
#   ParticleManager   —— 全局粒子管理器（汇集所有发射器，统一 update/render）
#
# 纹理替换接口：
#   每颗粒子的 texture 字段默认为 None → 渲染几何图形。
#   未来替换美术资源时，只需设置 particle.texture = sprite_surface，
#   或将 PresetEmitters 中的 texture 参数改为精灵表切片。
#
# 依附模式：
#   emitter.attach_entity = some_entity → 粒子跟随实体移动
#   （毒/烧/冰/流血 粒子挂在受影响实体身上）
#
# 屏幕空间：
#   emitter.screen_space = True → 粒子不受摄像机偏移影响
#   （弹反金色闪光）
# =============================================================
from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple, Dict, Any

import pygame

from config import LAYER_PARTICLE


# =============================================================
# 单颗粒子
# =============================================================

class Particle:
    """
    单颗粒子。

    生命周期：spawn → update (每帧) → 过期自动移除。

    纹理替换接口：
      - texture: Optional[pygame.Surface]
        None → 渲染几何图形（shape + color + size）
        设置后 → blit 纹理，忽略 shape/color/size

    使用示例：
        p = Particle(x=100, y=200, vx=50, vy=-120, lifetime=0.5,
                     color=(255,60,60), size=3, shape="circle")
    """

    __slots__ = (
        "x", "y", "vx", "vy",
        "lifetime", "elapsed",
        "color", "size", "start_size", "end_size",
        "alpha", "start_alpha", "end_alpha",
        "gravity", "shape",
        "texture",          # 纹理替换接口
        "_alive",
    )

    def __init__(self,
                 x: float = 0, y: float = 0,
                 vx: float = 0, vy: float = 0,
                 lifetime: float = 1.0,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 size: float = 4.0,
                 end_size: float = -1.0,
                 alpha: int = 255,
                 end_alpha: int = 0,
                 gravity: float = 0.0,
                 shape: str = "circle",
                 texture: Optional[pygame.Surface] = None):
        self.x: float = float(x)
        self.y: float = float(y)
        self.vx: float = float(vx)
        self.vy: float = float(vy)

        self.lifetime: float = max(0.01, lifetime)
        self.elapsed: float = 0.0

        self.color: Tuple[int, int, int] = color
        self.size: float = float(size)
        self.start_size: float = float(size)
        self.end_size: float = float(end_size if end_size >= 0 else size)

        self.alpha: int = alpha
        self.start_alpha: int = alpha
        self.end_alpha: int = end_alpha

        self.gravity: float = float(gravity)
        self.shape: str = shape       # "circle" | "square" | "diamond"

        self.texture: Optional[pygame.Surface] = texture

        self._alive: bool = True

    # ----------------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        return self._alive

    def update(self, dt: float) -> None:
        """
        每帧更新位置、速度、透明度。

        返回后调用方应检查 is_alive；若已死亡则从发射器移除。
        """
        if not self._alive:
            return

        self.elapsed += dt
        if self.elapsed >= self.lifetime:
            self._alive = False
            return

        # 运动
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt

        # 线性插值：size
        t = self.elapsed / self.lifetime
        self.size = self.start_size + (self.end_size - self.start_size) * t

        # 线性插值：alpha
        self.alpha = int(self.start_alpha + (self.end_alpha - self.start_alpha) * t)
        self.alpha = max(0, min(255, self.alpha))

    def render(self, surface: pygame.Surface,
               camera_x: float = 0, camera_y: float = 0) -> None:
        """
        绘制粒子到目标 surface。

        :param surface:  目标画布
        :param camera_x: 摄像机世界 X 偏移
        :param camera_y: 摄像机世界 Y 偏移
        """
        if not self._alive:
            return

        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        sz = max(1, int(self.size))

        # ---- 纹理模式 ----
        if self.texture is not None:
            img = self.texture.copy()
            img.set_alpha(self.alpha)
            # 缩放到当前 size
            if sz != img.get_width():
                img = pygame.transform.scale(img, (sz, sz))
            surface.blit(img, (sx - sz // 2, sy - sz // 2))
            return

        # ---- 几何模式 ----
        r, g, b = self.color
        color_with_alpha = (r, g, b, self.alpha)

        # 创建临时带 alpha 的 surface（避免修改全局颜色）
        temp = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)

        if self.shape == "circle":
            pygame.draw.circle(temp, color_with_alpha, (sz, sz), sz)
        elif self.shape == "square":
            pygame.draw.rect(temp, color_with_alpha, (0, 0, sz * 2, sz * 2))
        elif self.shape == "diamond":
            half = sz
            points = [(half, 0), (half * 2, half), (half, half * 2), (0, half)]
            pygame.draw.polygon(temp, color_with_alpha, points)
        else:
            pygame.draw.circle(temp, color_with_alpha, (sz, sz), sz)

        surface.blit(temp, (sx - sz, sy - sz))

    def kill(self) -> None:
        """立即销毁粒子。"""
        self._alive = False

    def __repr__(self) -> str:
        return (f"<Particle ({self.x:.0f},{self.y:.0f}) "
                f"t={self.elapsed:.2f}/{self.lifetime:.2f} alive={self._alive}>")


# =============================================================
# 粒子发射器
# =============================================================

class ParticleEmitter:
    """
    粒子发射器：管理一组粒子并按配置生成。

    依附模式：
      attach_entity = entity → 每帧同步发射位置到实体坐标
      （用于毒/烧/冰/流血等状态粒子）

    屏幕空间：
      screen_space = True → 渲染时忽略摄像机偏移
      （用于弹反闪光等 UI 级特效）

    纹理替换接口：
      particle_texture: Optional[pygame.Surface]
      设置后所有新生成粒子将使用该纹理而非几何图形。
    """

    def __init__(self,
                 name: str = "emitter",
                 attach_entity=None,
                 screen_space: bool = False):
        self.name: str = name
        self.particles: List[Particle] = []

        # 依附实体：粒子跟随实体位置
        self.attach_entity = None
        if attach_entity is not None:
            self.attach_entity = attach_entity

        # 屏幕空间渲染
        self.screen_space: bool = screen_space

        # 上一次依附实体位置（用于计算 velocity 延续）
        self._last_attach_x: float = 0.0
        self._last_attach_y: float = 0.0

        # ---- 生成参数（可通过 configure 修改） ----
        self.spawn_count: int = 8
        self.lifetime_min: float = 0.3
        self.lifetime_max: float = 0.6
        self.speed_min: float = 80.0
        self.speed_max: float = 250.0
        self.angle_min: float = -60.0    # 度，0°=向上
        self.angle_max: float = 60.0
        self.color: Tuple[int, int, int] = (200, 30, 30)
        self.color_variance: int = 30     # 颜色随机偏差
        self.size_min: float = 2.0
        self.size_max: float = 5.0
        self.end_size_min: float = 0.0
        self.end_size_max: float = 2.0
        self.gravity: float = 300.0
        self.gravity_variance: float = 100.0
        self.shape: str = "circle"

        # 纹理替换
        self.particle_texture: Optional[pygame.Surface] = None

        # 透明度
        self.start_alpha: int = 255
        self.end_alpha: int = 0

        # 自动清理：发射器无粒子后是否标记为完成
        self.auto_remove: bool = True
        self._finished: bool = False

        # 每帧持续生成（用于毒/烧等持续特效）
        self.continuous: bool = False
        self.spawn_interval: float = 0.1    # 连续生成间隔（秒）
        self._spawn_timer: float = 0.0

    # ----------------------------------------------------------------
    # 配置
    # ----------------------------------------------------------------

    def configure(self, **kwargs) -> "ParticleEmitter":
        """
        链式配置发射器参数。

        可配置字段：spawn_count, lifetime_min, lifetime_max,
        speed_min, speed_max, angle_min, angle_max, color, color_variance,
        size_min, size_max, end_size_min, end_size_max, gravity, gravity_variance,
        shape, particle_texture, start_alpha, end_alpha, auto_remove,
        continuous, spawn_interval
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self

    def get_attach_position(self) -> Tuple[float, float]:
        """获取依附实体的当前世界坐标。"""
        if self.attach_entity is None:
            return 0.0, 0.0
        entity = self.attach_entity
        x = getattr(entity, "x", 0.0)
        y = getattr(entity, "y", 0.0)
        # 优先取 rect 中心
        if hasattr(entity, "rect") and entity.rect is not None:
            x = float(entity.rect.centerx)
            y = float(entity.rect.centery)
        return x, y

    # ----------------------------------------------------------------
    # 生成
    # ----------------------------------------------------------------

    def emit(self, count: int = -1, position: Optional[Tuple[float, float]] = None) -> None:
        """
        发射一批粒子。

        :param count:    数量（-1 = 使用 self.spawn_count）
        :param position: 发射中心 (world_x, world_y)；None 则使用依附实体位置
        """
        n = count if count > 0 else self.spawn_count
        if n <= 0:
            return

        if position is not None:
            cx, cy = position
        else:
            cx, cy = self.get_attach_position()

        # 更新上一次位置（用于速度延续）
        self._last_attach_x = cx
        self._last_attach_y = cy

        for _ in range(n):
            p = self._create_particle(cx, cy)
            self.particles.append(p)

    def emit_single(self, x: float, y: float) -> Particle:
        """手动发射单颗粒子并返回引用（精细控制用）。"""
        p = self._create_particle(x, y)
        self.particles.append(p)
        return p

    def _create_particle(self, cx: float, cy: float) -> Particle:
        """内部：按当前配置创建一颗粒子。"""
        # 随机角度（度 → 弧度）
        angle_deg = random.uniform(self.angle_min, self.angle_max)
        angle_rad = math.radians(angle_deg)

        speed = random.uniform(self.speed_min, self.speed_max)
        vx = math.cos(angle_rad) * speed
        vy = -math.sin(angle_rad) * speed  # 屏幕坐标系 Y 向下，取反

        lifetime = random.uniform(self.lifetime_min, self.lifetime_max)
        size = random.uniform(self.size_min, self.size_max)
        end_size = random.uniform(self.end_size_min, self.end_size_max)

        # 颜色随机偏差
        r = min(255, max(0, self.color[0] + random.randint(-self.color_variance, self.color_variance)))
        g = min(255, max(0, self.color[1] + random.randint(-self.color_variance, self.color_variance)))
        b = min(255, max(0, self.color[2] + random.randint(-self.color_variance, self.color_variance)))

        gravity = self.gravity + random.uniform(-self.gravity_variance, self.gravity_variance)

        # 初始位置随机偏移（避免所有粒子从同一点出发）
        ox = random.uniform(-4, 4)
        oy = random.uniform(-4, 4)

        return Particle(
            x=cx + ox, y=cy + oy,
            vx=vx, vy=vy,
            lifetime=lifetime,
            color=(r, g, b),
            size=size,
            end_size=end_size,
            alpha=self.start_alpha,
            end_alpha=self.end_alpha,
            gravity=gravity,
            shape=self.shape,
            texture=self.particle_texture,
        )

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        """
        推进所有粒子 + 连续生成 + 依附实体同步。

        调用后 emitter.is_finished 可能变为 True（无粒子 + auto_remove）。
        """
        # 依附同步
        if self.attach_entity is not None:
            ax, ay = self.get_attach_position()
            self._last_attach_x = ax
            self._last_attach_y = ay

        # 连续生成
        if self.continuous:
            self._spawn_timer += dt
            interval = max(0.01, self.spawn_interval)
            while self._spawn_timer >= interval:
                self._spawn_timer -= interval
                self.emit(count=1)

        # 更新粒子
        for p in self.particles:
            p.update(dt)

        # 清理死亡粒子
        self.particles = [p for p in self.particles if p.is_alive]

        # 自动标记完成
        if self.auto_remove and not self.particles and not self.continuous:
            self._finished = True

    def render(self, surface: pygame.Surface,
               camera_x: float = 0, camera_y: float = 0) -> None:
        """绘制所有活跃粒子。"""
        if self.screen_space:
            camera_x, camera_y = 0, 0

        for p in self.particles:
            p.render(surface, camera_x, camera_y)

    # ----------------------------------------------------------------
    # 控制
    # ----------------------------------------------------------------

    def clear(self) -> None:
        """移除所有粒子。"""
        self.particles.clear()
        self._finished = True

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def alive_count(self) -> int:
        return len(self.particles)

    def __repr__(self) -> str:
        return (f"<ParticleEmitter '{self.name}' particles={self.alive_count} "
                f"finished={self._finished}>")


# =============================================================
# 预设发射器工厂
# =============================================================

class PresetEmitters:
    """
    预设发射器的静态工厂方法集合。

    每种预设返回一个已配置好的 ParticleEmitter，可直接使用：
        emitter = PresetEmitters.blood_splash()
        emitter.emit(count=8, position=(enemy_x, enemy_y))
        particle_mgr.add(emitter)

    纹理替换：
        未来替换美术资源时，在工厂方法中设置 .particle_texture = loaded_sprite
        或在创建后 emitter.configure(particle_texture=my_sprite)
    """

    @staticmethod
    def blood_splash() -> ParticleEmitter:
        """血溅粒子：红色小圆向两侧飞溅，受重力下落。"""
        return ParticleEmitter(name="blood_splash").configure(
            spawn_count=8,
            lifetime_min=0.25, lifetime_max=0.55,
            speed_min=120, speed_max=320,
            angle_min=30, angle_max=150,       # 偏左右
            color=(200, 30, 30), color_variance=40,
            size_min=2.0, size_max=5.0,
            end_size_min=0.5, end_size_max=1.5,
            gravity=300, gravity_variance=150,
            shape="circle",
            start_alpha=255, end_alpha=0,
            auto_remove=True,
        )

    @staticmethod
    def parry_flash() -> ParticleEmitter:
        """
        弹反金色闪光：大光圈从中心向外扩散并快速消退。
        屏幕空间渲染（不受摄像机影响）。
        """
        emitter = ParticleEmitter(
            name="parry_flash",
            screen_space=True,
        ).configure(
            spawn_count=1,
            lifetime_min=0.35, lifetime_max=0.35,
            speed_min=0, speed_max=1,       # 几乎不移动
            angle_min=0, angle_max=0,
            color=(255, 215, 50), color_variance=20,
            size_min=30, size_max=30,
            end_size_min=200, end_size_max=250,
            gravity=0,
            shape="circle",
            start_alpha=200, end_alpha=0,
            auto_remove=True,
        )
        # 定制：大光圈只生成 1 颗（size 扩散即可）
        emitter.spawn_count = 1
        return emitter

    @staticmethod
    def poison_bubbles(attach_entity=None) -> ParticleEmitter:
        """中毒气泡：绿色小圆从实体位置上升、摇摆。"""
        return ParticleEmitter(
            name="poison",
            attach_entity=attach_entity,
        ).configure(
            spawn_count=1,
            lifetime_min=0.8, lifetime_max=1.5,
            speed_min=20, speed_max=60,
            angle_min=70, angle_max=110,      # 偏上
            color=(60, 200, 60), color_variance=30,
            size_min=2.0, size_max=5.0,
            end_size_min=1.0, end_size_max=3.0,
            gravity=-30,                       # 轻微上浮
            shape="circle",
            start_alpha=200, end_alpha=0,
            continuous=True,
            spawn_interval=0.15,
            auto_remove=False,
        )

    @staticmethod
    def burn_fire(attach_entity=None) -> ParticleEmitter:
        """燃烧火焰：橙红粒子从实体上方冒起。"""
        return ParticleEmitter(
            name="burn",
            attach_entity=attach_entity,
        ).configure(
            spawn_count=1,
            lifetime_min=0.3, lifetime_max=0.7,
            speed_min=30, speed_max=100,
            angle_min=60, angle_max=120,       # 向上为主
            color=(255, 120, 30), color_variance=40,
            size_min=3.0, size_max=7.0,
            end_size_min=1.0, end_size_max=3.0,
            gravity=-80,                        # 上升后减速
            shape="circle",
            start_alpha=230, end_alpha=0,
            continuous=True,
            spawn_interval=0.08,
            auto_remove=False,
        )

    @staticmethod
    def freeze_crystals(attach_entity=None) -> ParticleEmitter:
        """冰冻冰晶：蓝白色小方块从实体表面散落。"""
        return ParticleEmitter(
            name="freeze",
            attach_entity=attach_entity,
        ).configure(
            spawn_count=1,
            lifetime_min=0.4, lifetime_max=1.0,
            speed_min=10, speed_max=50,
            angle_min=30, angle_max=150,
            color=(100, 200, 255), color_variance=30,
            size_min=2.0, size_max=5.0,
            end_size_min=0.5, end_size_max=1.5,
            gravity=150,
            shape="square",
            start_alpha=220, end_alpha=0,
            continuous=True,
            spawn_interval=0.2,
            auto_remove=False,
        )

    @staticmethod
    def bleed_drip(attach_entity=None) -> ParticleEmitter:
        """流血滴落：深红色粒子从实体向下滴。"""
        return ParticleEmitter(
            name="bleed",
            attach_entity=attach_entity,
        ).configure(
            spawn_count=1,
            lifetime_min=0.5, lifetime_max=1.2,
            speed_min=10, speed_max=40,
            angle_min=80, angle_max=100,        # 向下为主
            color=(160, 20, 20), color_variance=20,
            size_min=2.0, size_max=4.0,
            end_size_min=1.0, end_size_max=2.0,
            gravity=200,
            shape="circle",
            start_alpha=200, end_alpha=0,
            continuous=True,
            spawn_interval=0.25,
            auto_remove=False,
        )

    @staticmethod
    def dust_cloud() -> ParticleEmitter:
        """灰尘/尘烟：灰棕色圆形扩散，用于翻滚/落地。"""
        return ParticleEmitter(name="dust").configure(
            spawn_count=6,
            lifetime_min=0.3, lifetime_max=0.7,
            speed_min=30, speed_max=100,
            angle_min=20, angle_max=160,
            color=(140, 120, 90), color_variance=30,
            size_min=3.0, size_max=8.0,
            end_size_min=2.0, end_size_max=6.0,
            gravity=-20,
            shape="circle",
            start_alpha=150, end_alpha=0,
            auto_remove=True,
        )

    @staticmethod
    def magic_spark() -> ParticleEmitter:
        """魔法光效：紫色闪烁星点扩散。"""
        return ParticleEmitter(name="magic").configure(
            spawn_count=10,
            lifetime_min=0.2, lifetime_max=0.5,
            speed_min=60, speed_max=200,
            angle_min=0, angle_max=360,
            color=(180, 100, 255), color_variance=40,
            size_min=2.0, size_max=5.0,
            end_size_min=0.5, end_size_max=1.5,
            gravity=100,
            shape="diamond",
            start_alpha=255, end_alpha=0,
            auto_remove=True,
        )

    @staticmethod
    def fire_embers() -> ParticleEmitter:
        """火星粒子：用于营火点燃等场景。"""
        return ParticleEmitter(name="embers").configure(
            spawn_count=5,
            lifetime_min=0.5, lifetime_max=1.5,
            speed_min=30, speed_max=80,
            angle_min=60, angle_max=120,
            color=(255, 180, 40), color_variance=50,
            size_min=1.0, size_max=3.0,
            end_size_min=0.3, end_size_max=1.0,
            gravity=-50,
            shape="circle",
            start_alpha=230, end_alpha=0,
            auto_remove=True,
        )

    @staticmethod
    def boss_phase_burst() -> ParticleEmitter:
        """Boss 转阶段爆裂光效：暗红/紫色大范围扩散。"""
        return ParticleEmitter(name="phase_burst").configure(
            spawn_count=20,
            lifetime_min=0.4, lifetime_max=1.0,
            speed_min=150, speed_max=400,
            angle_min=0, angle_max=360,
            color=(200, 50, 150), color_variance=50,
            size_min=3.0, size_max=8.0,
            end_size_min=0.5, end_size_max=2.0,
            gravity=200,
            shape="circle",
            start_alpha=255, end_alpha=0,
            auto_remove=True,
        )


# =============================================================
# 全局粒子管理器
# =============================================================

class ParticleManager:
    """
    全局粒子管理器。

    用法：
        mgr = ParticleManager()

        # 发射粒子
        mgr.spawn("blood_splash", position=(enemy_x, enemy_y))
        mgr.spawn("parry_flash", screen_pos=(screen_cx, screen_cy))

        # 挂载状态粒子到实体
        emitter = mgr.attach("poison", entity=enemy)
        # 状态消失时移除
        mgr.remove_attached("poison", entity=enemy)

        # 每帧
        mgr.update(dt)
        mgr.render(screen, camera_x, camera_y)
    """

    def __init__(self):
        self._emitters: List[ParticleEmitter] = []

        # 预设工厂映射
        self._presets: Dict[str, callable] = {
            "blood_splash":   PresetEmitters.blood_splash,
            "parry_flash":    PresetEmitters.parry_flash,
            "poison":         PresetEmitters.poison_bubbles,
            "burn":           PresetEmitters.burn_fire,
            "freeze":         PresetEmitters.freeze_crystals,
            "bleed":          PresetEmitters.bleed_drip,
            "dust":           PresetEmitters.dust_cloud,
            "magic":          PresetEmitters.magic_spark,
            "embers":         PresetEmitters.fire_embers,
            "phase_burst":    PresetEmitters.boss_phase_burst,
        }

        # 依附实体注册表：{(emitter_name, id(entity)): emitter}
        self._attached: Dict[Tuple[str, int], ParticleEmitter] = {}

    # ----------------------------------------------------------------
    # 发射
    # ----------------------------------------------------------------

    def spawn(self,
              preset_name: str,
              position: Optional[Tuple[float, float]] = None,
              screen_pos: Optional[Tuple[float, float]] = None,
              count: Optional[int] = None) -> Optional[ParticleEmitter]:
        """
        发射一次性粒子效果。

        :param preset_name: 预设名称（如 "blood_splash", "parry_flash"）
        :param position:    世界坐标 (x, y)
        :param screen_pos:  屏幕坐标 (x, y)——用于 screen_space 发射器
        :param count:       覆盖默认数量
        :return:            创建的发射器引用（可用于后续手动移除）
        """
        factory = self._presets.get(preset_name)
        if factory is None:
            return None

        emitter = factory()

        if screen_pos is not None:
            emitter.screen_space = True
            spawn_pos = screen_pos
        elif position is not None:
            spawn_pos = position
        else:
            spawn_pos = (0, 0)

        emitter.emit(count=count if count is not None else -1, position=spawn_pos)
        self._emitters.append(emitter)
        return emitter

    def attach(self, preset_name: str, entity) -> Optional[ParticleEmitter]:
        """
        将粒子效果挂载到实体上（用于持续状态：毒/烧/冰/流血）。

        :param preset_name: 预设名称
        :param entity:      要挂载的实体
        :return:            创建的发射器引用
        """
        factory = self._presets.get(preset_name)
        if factory is None:
            return None

        emitter = factory(attach_entity=entity)

        key = (preset_name, id(entity))
        # 如果已有同名发射器挂在同实体，先清理
        if key in self._attached:
            self._attached[key].clear()
        self._attached[key] = emitter
        self._emitters.append(emitter)
        return emitter

    def remove_attached(self, preset_name: str, entity) -> None:
        """
        移除实体上挂载的指定类型粒子。

        :param preset_name: 预设名称
        :param entity:      实体
        """
        import logging
        _log = logging.getLogger(__name__)
        key = (preset_name, id(entity))
        _log.debug("ParticleManager.remove_attached: key=%s found=%s",
                   key, key in self._attached)
        if key in self._attached:
            self._attached[key].clear()
            del self._attached[key]

    def remove_all_attached(self, entity) -> None:
        """移除实体上的所有挂载粒子。"""
        eid = id(entity)
        keys_to_remove = [k for k in self._attached if k[1] == eid]
        for k in keys_to_remove:
            self._attached[k].clear()
            del self._attached[k]

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float) -> None:
        """更新所有发射器，清理已完成的。"""
        for emitter in self._emitters:
            emitter.update(dt)

        # 清理已完成的发射器 + 对应的依附注册
        finished = [e for e in self._emitters if e.is_finished]
        for e in finished:
            # 同步清理依附表
            keys_to_del = [k for k, v in self._attached.items() if v is e]
            for k in keys_to_del:
                del self._attached[k]
        self._emitters = [e for e in self._emitters if not e.is_finished]

    def render(self, surface: pygame.Surface,
               camera_x: float = 0, camera_y: float = 0) -> None:
        """渲染所有活跃发射器。"""
        for emitter in self._emitters:
            emitter.render(surface, camera_x, camera_y)

    # ----------------------------------------------------------------
    # 控制
    # ----------------------------------------------------------------

    def clear(self) -> None:
        """清空所有发射器（场景退出时调用）。"""
        for e in self._emitters:
            e.clear()
        self._emitters.clear()
        self._attached.clear()

    @property
    def total_particles(self) -> int:
        """当前活跃粒子总数。"""
        return sum(e.alive_count for e in self._emitters)

    @property
    def emitter_count(self) -> int:
        return len(self._emitters)

    def register_preset(self, name: str, factory: callable) -> None:
        """注册自定义预设。"""
        self._presets[name] = factory

    def __repr__(self) -> str:
        return (f"<ParticleManager emitters={self.emitter_count} "
                f"particles={self.total_particles}>")
