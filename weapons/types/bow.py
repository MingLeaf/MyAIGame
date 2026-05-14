# =============================================================
# weapons/types/bow.py —— 弓
#
# 定位：
#   远程武器。轻攻击 = 普通箭、重攻击 = 蓄力箭，
#   攻击通过生成 Arrow 抛射物完成，需消耗 items.consumables.arrow。
#
# 战技：穿云箭（Piercing Arrow）
#   - 消耗 25 灵力 + 1 支箭矢
#   - 直线高速箭矢，可穿透多个敌人，伤害 = 重攻击 × 1.8
#   - 不受重力（lifetime 短）
#
# 弹药消耗约定（item id："arrow"）：
#   PlayerCombat / 攻击状态在为弓生成命中前，先调用：
#       Bow.consume_arrow(player) -> bool
#   返回 False 时跳过本次攻击。
#   第 6 阶段已实装 items.consumables.arrow.ArrowItem，弹药消耗为强制要求：
#     - 玩家有 inventory 且 inventory 中无 'arrow' → 返回 False，
#       并发布 'weapon_no_ammo' 事件提示 UI；
#     - 玩家没有 inventory（脚本 / 测试场景）→ 视为通过（保留测试便利）。
# =============================================================
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from weapons.base_weapon import BaseWeapon, WeaponType, AttackData
from weapons.weapon_art  import WeaponArt
from core.event_manager  import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


# 箭矢物品 ID（对应未实装的 items.consumables.arrow.ArrowItem）
ARROW_ITEM_ID = "arrow"


def _consume_arrow(player: "Player") -> bool:
    """
    尝试从玩家背包消耗 1 支箭矢。
    返回 True 表示成功（或测试场景无 inventory），False 表示明确缺箭。
    """
    inv = getattr(player, "inventory", None)
    # 没有完整背包接口 → 测试 / 调试场景，按通过
    if inv is None or not hasattr(inv, "count") or not hasattr(inv, "remove_item_id"):
        return True
    cnt = inv.count(ARROW_ITEM_ID)
    if cnt <= 0:
        # 明确缺箭：拒绝发射并通知 UI
        event_manager.emit("weapon_no_ammo", {
            "weapon_type": "bow", "ammo_id": ARROW_ITEM_ID,
        })
        return False
    inv.remove_item_id(ARROW_ITEM_ID, 1)
    return True


def _spawn_arrow(player: "Player", area, *,
                 vx_base: float = 700.0,
                 damage: int = 15,
                 element: str = "physical",
                 poise_damage: float = 8.0,
                 piercing: bool = False,
                 lifetime: float = 4.0):
    """生成一支 Arrow 抛射物并加入 area.projectiles。"""
    from physics.projectile import Arrow
    facing = player.facing or 1
    vx = vx_base * facing
    vy = -40.0   # 微仰角
    arrow = Arrow(
        x = player.rect.centerx + facing * 18,
        y = player.rect.centery - 4,
        vx = vx,
        vy = vy,
        damage = damage,
        owner = player,
        element = element,
        poise_damage = poise_damage,
        lifetime = lifetime,
    )
    if piercing:
        # 穿透标记（命中后不销毁）
        try:
            arrow.piercing = True   # type: ignore[attr-defined]
        except Exception:
            pass
    if area is not None and hasattr(area, "projectiles"):
        area.projectiles.append(arrow)
    return arrow


class BowPiercingArrowArt(WeaponArt):
    """弓战技：穿云箭。"""

    art_id        = "bow_piercing_arrow"
    display_name  = "穿云箭"
    mana_cost     = 25
    cooldown      = 1.8
    poise_damage  = 18.0
    description   = "高速穿透箭，可命中多个敌人"

    def _check_resources(self, player: "Player") -> bool:
        if not super()._check_resources(player):
            return False
        # 严格校验箭矢库存（第 6 阶段后已强制要求）：
        #   - 玩家有 inventory 且 inventory 中无箭 → 拒绝
        #   - 玩家无 inventory（脚本/测试场景）→ 通过
        inv = getattr(player, "inventory", None)
        if inv is not None and hasattr(inv, "count"):
            if inv.count(ARROW_ITEM_ID) < 1:
                event_manager.emit("weapon_no_ammo", {
                    "weapon_type": "bow", "ammo_id": ARROW_ITEM_ID,
                })
                return False
        return True

    def _consume_resources(self, player: "Player") -> None:
        super()._consume_resources(player)
        _consume_arrow(player)

    def _execute(self, player: "Player", area) -> None:
        weapon = player.weapon
        wd = weapon.get_heavy_attack()
        _spawn_arrow(
            player, area,
            vx_base       = 950.0,
            damage        = int(wd.damage * 1.8),
            element       = wd.element,
            poise_damage  = self.poise_damage,
            piercing      = True,
            lifetime      = 1.5,
        )


class Bow(BaseWeapon):
    """
    长弓 —— 远程武器。

    轻攻击：8 / 9 / 11（普通箭速射，需要箭矢）
    重攻击：18（蓄力箭）
    元素：physical
    """

    weapon_type  = WeaponType.BOW
    display_name = "猎人长弓"
    color        = (160, 100, 60)

    _base_light_dmg  = 8
    _base_heavy_dmg  = 18
    _element         = "physical"

    _light_stamina   = 10.0
    _heavy_stamina   = 24.0

    _light_knockback = 80.0     # 弓近战推距弱
    _heavy_knockback = 160.0

    # 弓的近战 hitbox 较小（只有作为兜底，主要靠 Arrow）
    _hb_offset_x   = 14
    _hb_offset_y   = 0
    _hb_w_light    = 22
    _hb_h_light    = 24
    _hb_w_heavy    = 28
    _hb_h_heavy    = 28
    _active_f_light = 4
    _active_f_heavy = 6

    _light_combo_mult = (1.0, 1.10, 1.30)
    _bleed_stack_light  = 0.0
    _poison_stack_light = 0.0

    _weapon_art_mana_cost = 25

    def __init__(self):
        super().__init__()
        self.weapon_art_obj = BowPiercingArrowArt()

    # ----------------------------------------------------------------
    # 弓特有：发射箭矢（由 PlayerCombat / 攻击状态调用）
    # ----------------------------------------------------------------

    @staticmethod
    def consume_arrow(player: "Player") -> bool:
        """对外暴露的箭矢消耗接口（玩家攻击状态可在判定前调用）。"""
        return _consume_arrow(player)

    def fire_arrow(self, player: "Player", area, *, is_heavy: bool = False):
        """
        生成一支普通箭。
        :param is_heavy: 重攻击 → 伤害更高、初速更快、有重力。
        """
        if not _consume_arrow(player):
            return None
        if is_heavy:
            wd = self.get_heavy_attack()
            return _spawn_arrow(
                player, area,
                vx_base=820.0,
                damage=wd.damage,
                element=wd.element,
                poise_damage=wd.poise_damage,
                lifetime=4.0,
            )
        else:
            wd = self.get_light_attack(0)
            return _spawn_arrow(
                player, area,
                vx_base=700.0,
                damage=wd.damage,
                element=wd.element,
                poise_damage=wd.poise_damage,
                lifetime=4.0,
            )
