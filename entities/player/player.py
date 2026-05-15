# =============================================================
# entities/player/player.py —— 玩家主类
# =============================================================
from __future__ import annotations
from typing import List, TYPE_CHECKING
import pygame

from entities.base_entity import BaseEntity
from physics.gravity      import GravitySystem
from physics.movement_resolver import MovementResolver
from entities.player.player_stats  import PlayerStats
from entities.player.growth_stats  import GrowthStats
from entities.player.attack_hitbox import AttackHitbox
from entities.player.player_combat import PlayerCombat
from entities.player.player_states import (
    IdleState, RunState, JumpState, FallState,
    RollState,
    LightAttack1State, LightAttack2State, LightAttack3State,
    HeavyAttackState,
    HurtState, DeadState, BlockState,
)
from utils.state_machine  import StateMachine
from core.input_handler   import input_handler
from core.event_manager   import event_manager
from utils.color          import WHITE
from weapons.sword        import Sword
from player.inventory     import Inventory
from player.equipment     import Equipment
from player.player_build  import PlayerBuild
from items.equipment.set_bonus import SetBonusManager
from items.item_database  import item_db
import utils.debug as debug

if TYPE_CHECKING:
    from map.collision_map import CollisionMap


# ---- 玩家尺寸 & 速度 ----
PLAYER_W     = 24
PLAYER_H     = 48
PLAYER_SPEED = 240.0
PLAYER_COLOR = (80, 140, 220)

# 穿板持续帧数
PASS_THROUGH_FRAMES = 8


class Player(BaseEntity):
    """
    正式玩家类（替换第二阶段的 _TestPlayer）。
    - 状态机驱动所有动作
    - 内置 HP / Stamina / Mana 数值系统
    - 攻击判定框管理
    - 输入通过 core.input_handler 读取
    """

    # 是否在 __init__ 中自动发放初始装备 / 消耗品
    # 默认 False，避免单元测试受默认装备影响。
    # GameScene 在创建 Player 后会显式调用 grant_starting_kit()。
    GIVE_STARTING_KIT: bool = False

    def __init__(self, x: float, y: float):
        super().__init__(x, y, PLAYER_W, PLAYER_H)
        self.team = "player"  # 玩家阵营

        # 子系统
        self.stats    = PlayerStats()
        self.growth   = GrowthStats()          # 六项成长属性
        self.gravity  = GravitySystem()
        self.resolver = MovementResolver()
        self.inp      = input_handler

        # 当前装备武器（默认：骑士剑）
        self.weapon = Sword()

        # 初始化时同步一次成长属性
        self.stats.apply_growth(self.growth, self.weapon)

        # ---- 背包 / 装备栏 / Build 系统 ----
        self.inventory  = Inventory()           # 30 格背包
        self.equipment  = Equipment(self)       # 6 槽装备栏
        self.build      = PlayerBuild(self)     # 等级 + 属性分配
        # ---- 套装效果（监听 equipment_changed 自动激活/解除）----
        self.set_bonus  = SetBonusManager(self)
        self.set_bonus.register_many(item_db.set_bonuses)

        # ---- 战斗组件（第 4 阶段重构）----
        # 持有 BlockComponent + KnockbackComponent，统一处理受击/弹反/格挡
        self.combat = PlayerCombat(self)
        # 便捷别名（向旧逻辑暴露 self.block / self.kb）
        self.block  = self.combat.block
        self.kb     = self.combat.kb

        # ---- 第 7 阶段：发放初始装备 + 初始消耗品 ----
        # 默认仅在 GIVE_STARTING_KIT=True 时自动调用；
        # GameScene 通常在创建 Player 后显式调用 grant_starting_kit()
        if self.GIVE_STARTING_KIT:
            self.grant_starting_kit()

        # 状态机
        self.fsm = StateMachine(owner=self)
        self.fsm.add_states(
            IdleState(), RunState(), JumpState(), FallState(),
            RollState(),
            LightAttack1State(), LightAttack2State(), LightAttack3State(),
            HeavyAttackState(),
            HurtState(), DeadState(),
            BlockState(),
        )
        self.fsm.change_state("Idle")

        # 输入缓存（由 _read_input 每帧设置，状态消费后清零）
        self.jump_requested:         bool = False
        self.roll_requested:         bool = False
        self.light_attack_requested: bool = False
        self.heavy_attack_requested: bool = False
        self.weapon_art_requested:   bool = False

        # 当前所在区域引用（GameScene/area 在加载或每帧调用 set_area 设置，
        # 供战技生成抛射物使用）
        self.current_area = None

        # 土狼时间 & 跳跃缓冲
        self.coyote_timer: float = 0.0
        self._jump_buffer: float = 0.0

        # 下穿平台
        self._pass_through:        bool = False
        self._pass_through_frames: int  = 0

        # 无敌帧（翻滚）
        self.invincible: bool = False

        # 受击计时器（> 0 表示处于硬直中）
        self.hurt_timer: float = 0.0

        # 灵魂碎片（第 8 阶段：击败敌人 + 捡回遗物累积）
        self.soul_fragments: int = 0

        # 攻击判定框列表
        self.active_hitboxes: List[AttackHitbox] = []

        # 武器已在上方赋值，移除重复赋值

    # ================================================================
    # 每帧更新
    # ================================================================

    def update(self, dt: float, collision_map: "CollisionMap"):
        # 1. 读取输入，缓存到请求标志
        self._read_input()

        # 2. 更新受击计时器
        if self.hurt_timer > 0:
            self.hurt_timer -= dt

        # 2.5 战斗组件每帧更新（同步格挡/弹反窗口）
        block_pressed = self.inp.is_pressed("block")
        block_just    = self.inp.just_pressed("block")
        self.combat.update(dt, block_pressed, block_just)

        # 3. 更新数值系统（耐力恢复）
        self.stats.update(dt)

        # 4. 土狼时间计时
        if self.gravity.on_ground:
            self.coyote_timer = 0.10
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        # 5. 状态机驱动（状态内设置 vel_x）
        self.fsm.update(dt)

        # 5.5 击退速度叠加（从 KnockbackComponent 取值覆盖 vel_x）
        kb_vx = self.combat.consume_knockback(dt)
        if kb_vx != 0.0:
            self.vel_x = kb_vx

        # 6. 下穿平台计数器
        if self._pass_through_frames > 0:
            self._pass_through_frames -= 1
            self._pass_through = True
        else:
            self._pass_through = False

        # 7. 重力累积
        self.gravity.accumulate(dt)

        # 8. 移动解算
        new_rect, on_ground, new_vx, new_vy = self.resolver.resolve(
            self.rect,
            self.vel_x,
            self.gravity.vel_y,
            dt,
            collision_map,
            pass_through_platform=self._pass_through,
        )
        self.rect          = new_rect
        self.vel_x         = new_vx
        self.gravity.vel_y = new_vy
        self.gravity.set_on_ground(on_ground)

        # 9. 更新攻击判定框
        for hb in self.active_hitboxes:
            hb.update()
        self.active_hitboxes = [hb for hb in self.active_hitboxes if hb.active]

    # ================================================================
    # 输入读取
    # ================================================================

    def _read_input(self):
        inp = self.inp

        # 水平速度（Run/Idle 状态会设置，此处设置默认）
        axis = inp.axis_x
        if self.fsm.is_in("Run", "Idle", "Fall", "Jump"):
            self.vel_x = axis * PLAYER_SPEED
            if axis != 0:
                self.facing = axis

        # ---- 下穿平台 ----
        jump_just = inp.just_pressed("jump")
        if jump_just and inp.is_pressed("move_down") and self.gravity.on_ground:
            self._pass_through_frames = PASS_THROUGH_FRAMES
            self.gravity.vel_y        = 150.0
            self.gravity.on_ground    = False
            jump_just                 = False   # 消耗，不再触发跳跃

        # ---- 跳跃缓冲 ----
        if jump_just:
            self._jump_buffer = 0.12
        if self._jump_buffer > 0:
            self._jump_buffer -= 1 / 60   # 近似每帧递减
            if self.gravity.on_ground or self.coyote_timer > 0:
                self.jump_requested   = True
                self._jump_buffer     = 0.0

        # ---- 翻滚 ----
        # Shift 独立触发翻滚，在地面或空中均可（空中翻滚可后续扩展）
        if inp.just_pressed("roll") and self.gravity.on_ground:
            self.roll_requested = True

        # ---- 攻击 ----
        if inp.just_pressed("attack_light"):
            self.light_attack_requested = True
        if inp.just_pressed("attack_heavy"):
            self.heavy_attack_requested = True

        # ---- 战技 (U 键) ----
        if inp.just_pressed("weapon_art"):
            self.weapon_art_requested = True
            # 立即尝试触发；成功则消费请求
            if self.combat.try_weapon_art(self.current_area):
                self.weapon_art_requested = False

    # ================================================================
    # 受击接口（由伤害系统调用）
    # ================================================================

    def take_damage(self, amount: int, knockback_dir: int = 0, attacker=None,
                    *, element: str = "physical",
                    poise_damage: float = 10.0):
        """
        受到伤害。
        :param amount:        伤害值
        :param knockback_dir: 击退方向 (+1 向右 / -1 向左 / 0 不击退)
        :param attacker:      可选攻击者引用，用于弹反/格挡判定
        :param element:       攻击元素（physical / magic / fire / ice ...），
                              影响走护甲防御还是魔法抗性
        :param poise_damage:  韧性伤害（保留参数，后续阶段对接 PoiseComponent）
        """
        # 委托给战斗组件统一处理（含弹反 / 格挡 / 无敌帧 / 击退 / 装备减伤）
        return self.combat.take_damage(amount, knockback_dir, attacker,
                                       element=element,
                                       poise_damage=poise_damage)

    # ================================================================
    # 成长属性接口
    # ================================================================

    def allocate_stat(self, attr: str, points: int = 1) -> bool:
        """
        分配成长属性点并立即同步数值上限。

        示例：
            player.allocate_stat("vitality", 2)   # 加2点体魄
            player.allocate_stat("strength", 1)   # 加1点力量
        """
        ok = self.growth.allocate(attr, points)
        if ok:
            # 走完整同步（含 weapon_item_atk + armor_defense）
            if self.equipment is not None:
                self.equipment._sync_stats()
            else:
                self.stats.apply_growth(self.growth, self.weapon)
            event_manager.emit("player_stat_changed", {
                "attr": attr, "value": getattr(self.growth, attr)
            })
        return ok

    def equip_weapon(self, weapon) -> None:
        """
        便捷接口：通过 BaseWeapon 实例装备武器（向后兼容）。
        推荐改用 player.equipment.equip("weapon", weapon_item) 通过物品系统装备。
        """
        self.weapon = weapon
        self.stats.apply_growth(self.growth, self.weapon)
        event_manager.emit("player_weapon_changed", {
            "weapon": getattr(weapon, "display_name", ""),
            "roll_type": self.growth.roll_type,
        })

    # ================================================================
    # 初始装备发放
    # ================================================================

    # 发放清单（item_id, 数量）
    # 设计原则：让玩家一开始就能体验主要系统，但难度仍由敌人撑起
    _STARTING_INVENTORY = [
        # 消耗品 —— 类魂式补给
        ("heal_potion_small",   5),   # 5 瓶草药汤（× 30% HP）
        ("heal_potion_large",   1),   # 1 瓶高级圣水（满血）
        ("mana_potion_basic",   3),   # 3 瓶灵力药剂
        ("stamina_potion_basic", 2),  # 2 瓶精力饮剂
        ("antidote_universal",  2),   # 2 瓶万能解药
        # 强化类（鼓励试用 buff）
        ("buff_sharp_powder",   2),
        # 弹药 / 投掷物（让弓箭手玩家也能上手）
        ("arrow",              20),   # 20 支箭矢
        ("poison_dart",         3),   # 3 支毒飞镖
        # 灵核样本（暂时仅作测试）—— 可被削减
    ]

    # 装备槽（slot, item_id）
    _STARTING_EQUIPMENT = [
        ("weapon", "sword_iron"),     # 主武器：铁制骑士剑
        ("head",   "ranger_hood"),    # 游侠风帽（轻甲，保留快速翻滚）
        ("chest",  "ranger_vest"),
        ("hands",  "ranger_gloves"),
        ("legs",   "ranger_boots"),
    ]

    def grant_starting_kit(self) -> None:
        """
        给新建玩家发放初始装备 + 消耗品。
        数据驱动：通过 item_db.create() 创建，所有道具来自 data/items/*.json。

        幂等：重复调用会再次发放（占用更多背包格），调用方需自行控制。
        """
        # ---- 1. 装备武器 + 4 件游侠轻甲 ----
        for slot, item_id in self._STARTING_EQUIPMENT:
            item = item_db.create(item_id)
            if item is None:
                continue
            try:
                self.equipment.equip(slot, item)
            except Exception:
                # 槽位/类型异常时静默跳过（保持鲁棒性）
                continue

        # ---- 2. 填充背包 ----
        for item_id, qty in self._STARTING_INVENTORY:
            proto = item_db.create(item_id)
            if proto is None:
                continue
            try:
                self.inventory.add(proto, qty)
            except Exception:
                continue

        # ---- 3. 派发事件，让 UI 层显示"初始装备已发放" ----
        event_manager.emit("player_starting_kit_granted", {
            "weapon":     "sword_iron",
            "armor_set":  "ranger",
            "potion_count": sum(q for iid, q in self._STARTING_INVENTORY
                                if iid.startswith("heal_") or iid.startswith("mana_")
                                or iid.startswith("stamina_")),
        })

    # 保留旧别名（万一外部代码已引用）
    _grant_starting_kit = grant_starting_kit

    # ================================================================
    # 渲染
    # ================================================================

    def render(self, surface: pygame.Surface, cam_offset: tuple):
        ox, oy = cam_offset
        screen_rect = self.rect.move(-ox, -oy)

        # 根据状态选择颜色
        state = self.fsm.current_name
        if state == "Dead":
            color = (80, 60, 60)
        elif state == "Hurt":
            color = (220, 80, 80)
        elif state in ("LightAttack1", "LightAttack2", "LightAttack3", "HeavyAttack"):
            color = (220, 200, 60)
        elif state == "Roll":
            color = (80, 200, 180)
        elif state == "Block":
            # 弹反窗口期高亮（青蓝），普通格挡（灰蓝）
            if self.combat.in_parry_window():
                color = (200, 240, 255)
            else:
                color = (110, 130, 180)
        else:
            color = PLAYER_COLOR

        pygame.draw.rect(surface, color, screen_rect)

        # 格挡时在身前画一道盾形条
        if state == "Block":
            shield_w = 6
            shield_h = screen_rect.height - 8
            shield_y = screen_rect.top + 4
            if self.facing > 0:
                shield_x = screen_rect.right + 1
            else:
                shield_x = screen_rect.left - shield_w - 1
            shield_color = (240, 230, 120) if self.combat.in_parry_window() \
                                          else (200, 200, 220)
            pygame.draw.rect(surface, shield_color,
                             (shield_x, shield_y, shield_w, shield_h))
            pygame.draw.rect(surface, (40, 40, 60),
                             (shield_x, shield_y, shield_w, shield_h), 1)

        # 眼睛（朝向指示）
        eye_x = screen_rect.centerx + (6 if self.facing > 0 else -6)
        eye_y = screen_rect.top + 12
        pygame.draw.circle(surface, WHITE, (eye_x, eye_y), 4)
        pygame.draw.circle(surface, (20, 20, 40), (eye_x + self.facing, eye_y), 2)

        # 攻击判定框（始终渲染，不依赖 debug）
        for hb in self.active_hitboxes:
            hb.render(surface, cam_offset)

        # 碰撞框
        self.render_debug(surface, cam_offset)

    # ================================================================
    # 属性快捷访问
    # ================================================================

    @property
    def is_dead(self) -> bool:
        return self.fsm.is_in("Dead")

    @property
    def current_state(self) -> str:
        return self.fsm.current_name
