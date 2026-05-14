# =============================================================
# weapons/base_weapon.py —— 武器基类
#
# 武器决定：
#   - 伤害数值（轻攻击 / 重攻击 / 连段倍率）
#   - 攻击元素（影响克制）
#   - 判定框尺寸偏移（影响攻击范围）
#   - 耐力消耗
#   - 流血/毒等状态积累量（每次命中叠加）
#
# 第 5 阶段扩展（向后兼容）：
#   - self.affixes:        附魔词条列表（WeaponAffix 实例），
#                          运行时改写 get_*_attack 输出
#   - self.upgrade_level:  +0 ~ +10 强化等级
#   - self.upgrade_route:  强化路线（none / sharp / heavy / blessed / elemental）
#   - self.weapon_art_obj: 战技对象（WeaponArt 实例，由子类装载）
# =============================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from weapons.affixes import WeaponAffix
    from weapons.weapon_art import WeaponArt


class WeaponType:
    SWORD      = "sword"        # 单手剑
    GREATSWORD = "greatsword"   # 大剑
    DAGGER     = "dagger"       # 匕首
    SPEAR      = "spear"        # 长矛
    AXE        = "axe"          # 战斧
    STAFF      = "staff"        # 法杖
    HOLY_TOME  = "holy_tome"    # 圣典
    BOW        = "bow"          # 弓


@dataclass
class AttackData:
    """
    单次攻击（轻1 / 轻2 / 轻3 / 重）的参数快照，
    由 BaseWeapon.get_light_attack() / get_heavy_attack() 返回，
    注入到攻击状态中创建 AttackHitbox。
    """
    damage:          int    = 10      # 命中伤害
    poise_damage:    float  = 10.0    # 韧性伤害
    knockback:       float  = 180.0   # 击退初速度
    stamina_cost:    float  = 15.0    # 耐力消耗
    element:         str    = "none"  # 攻击元素
    # 判定框相对玩家中心的偏移与尺寸
    hb_offset_x:     int    = 20      # 水平偏移（facing 方向）
    hb_offset_y:     int    = 0       # 垂直偏移
    hb_width:        int    = 40      # 判定框宽
    hb_height:       int    = 36      # 判定框高
    active_frames:   int    = 6       # 判定帧数
    # 状态积累量（每次命中叠加，0 = 不触发该状态）
    bleed_stack:     float  = 0.0
    poison_stack:    float  = 0.0
    burn_stack:      float  = 0.0     # 火焰积累（第 5 阶段·元素附魔）
    freeze_stack:    float  = 0.0     # 冰冻积累
    shock_stack:     float  = 0.0     # 雷击积累
    # 词条新增字段（默认 0 → 不影响旧逻辑）
    armor_pierce:    float  = 0.0     # 无视防御百分比 [0.0, 1.0]
    lifesteal:       float  = 0.0     # 吸血百分比 [0.0, 1.0]
    bonus_damage:    int    = 0       # 元素附加伤害（用于附魔词条）


class BaseWeapon:
    """
    武器基类。子类通过覆盖属性或重写 get_*_attack() 提供数值。

    挂载方式：
        player.weapon = Sword()

    攻击状态调用：
        data = player.weapon.get_light_attack(combo_step)
        # combo_step: 0/1/2 对应 轻攻击1/2/3 连段
        hb = AttackHitbox(owner_rect, facing,
                          data.hb_offset_x, data.hb_offset_y,
                          data.hb_width, data.hb_height,
                          data.damage, data.active_frames,
                          knockback=data.knockback,
                          stamina_damage=data.stamina_cost,
                          element=data.element,
                          poise_damage=data.poise_damage)
    """

    #: 武器类型标识
    weapon_type: str = WeaponType.SWORD

    #: 武器展示名称（中文）
    display_name: str = "武器"

    #: 武器占位颜色（用于 HUD 图标）
    color: tuple = (200, 200, 200)

    # ---- 基础伤害参数（子类覆盖） ----
    _base_light_dmg:  int   = 10
    _base_heavy_dmg:  int   = 20
    _element:         str   = "none"

    _light_stamina:   float = 15.0
    _heavy_stamina:   float = 30.0

    _light_knockback: float = 160.0
    _heavy_knockback: float = 280.0

    # 判定框默认参数（子类可覆盖）
    _hb_offset_x:  int = 20
    _hb_offset_y:  int = 0
    _hb_w_light:   int = 40
    _hb_h_light:   int = 36
    _hb_w_heavy:   int = 48
    _hb_h_heavy:   int = 44
    _active_f_light: int = 6
    _active_f_heavy: int = 8

    # 连段倍率（step 0/1/2）
    _light_combo_mult: tuple = (1.0, 1.1, 1.25)

    # 状态积累（每次命中叠加量，0 = 不触发）
    _bleed_stack_light:  float = 0.0
    _poison_stack_light: float = 0.0

    # 战技耗灵力（子类覆盖）
    _weapon_art_mana_cost: int = 20

    # ----------------------------------------------------------------
    # 构造（第 5 阶段引入；旧子类 Sword/Dagger/... 未定义 __init__，
    # 实例化时会自动调用本方法。所有 attr 默认值保证向后兼容。）
    # ----------------------------------------------------------------

    def __init__(self):
        self.affixes: List["WeaponAffix"] = []

        # 强化系统状态
        self.upgrade_level: int = 0          # 0 ~ 10
        self.upgrade_route: str = "none"     # none / sharp / heavy / blessed / elemental
        # 由 weapon_upgrade.WeaponUpgrade 在升级时计算并写入
        self._upgrade_dmg_mult:    float = 1.0
        self._upgrade_poise_mult:  float = 1.0
        self._upgrade_bleed_mult:  float = 1.0
        self._upgrade_elem_override: Optional[str] = None
        self._upgrade_bonus_dmg:   int   = 0

        # 战技实例（子类可在自身 __init__ 中赋值）
        self.weapon_art_obj: Optional["WeaponArt"] = None

    # ----------------------------------------------------------------
    # 词条管理
    # ----------------------------------------------------------------

    def add_affix(self, affix: "WeaponAffix") -> "BaseWeapon":
        """
        附加一个词条。同一个词条实例不会重复添加。
        返回 self 以支持链式调用：
            weapon.add_affix(LifestealAffix()).add_affix(SwiftAffix())
        """
        if affix is None:
            return self
        if affix not in self.affixes:
            self.affixes.append(affix)
            try:
                affix.on_attach(self)
            except Exception:
                pass
        return self

    def remove_affix(self, affix: "WeaponAffix") -> None:
        if affix in self.affixes:
            try:
                affix.on_detach(self)
            except Exception:
                pass
            self.affixes.remove(affix)

    def clear_affixes(self) -> None:
        for a in list(self.affixes):
            self.remove_affix(a)

    def has_affix(self, affix_cls) -> bool:
        return any(isinstance(a, affix_cls) for a in self.affixes)

    # ----------------------------------------------------------------
    # 强化接口（由 weapons.weapon_upgrade.WeaponUpgrade 调用）
    # ----------------------------------------------------------------

    def apply_upgrade(self, level: int, route: str = "none",
                      *,
                      dmg_mult: float = 1.0,
                      poise_mult: float = 1.0,
                      bleed_mult: float = 1.0,
                      elem_override: Optional[str] = None,
                      bonus_dmg: int = 0) -> None:
        """由 WeaponUpgrade 计算后调用，写入强化状态。"""
        self.upgrade_level         = max(0, min(int(level), 10))
        self.upgrade_route         = route or "none"
        self._upgrade_dmg_mult     = float(dmg_mult)
        self._upgrade_poise_mult   = float(poise_mult)
        self._upgrade_bleed_mult   = float(bleed_mult)
        self._upgrade_elem_override = elem_override
        self._upgrade_bonus_dmg    = int(bonus_dmg)

    # ----------------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------------

    def get_light_attack(self, combo_step: int = 0) -> AttackData:
        """
        返回轻攻击参数（combo_step 0/1/2 对应三段连击）。
        子类可以完整重写此方法以自定义每段数值。

        韧性伤害设计基准（针对步兵 max_poise=20）：
          轻攻击每段约 4~6 点，需 4~5 次命中才能破韧步兵
          重攻击约 15~18 点，需 2 次才能破韧步兵
        """
        step  = max(0, min(combo_step, len(self._light_combo_mult) - 1))
        mult  = self._light_combo_mult[step]
        # 轻攻击韧性伤害：第一段4，第二段5，第三段6（随连段递增）
        poise_dmg = 4.0 + step * 1.0
        data = AttackData(
            damage       = max(1, int(self._base_light_dmg * mult)),
            poise_damage = poise_dmg,
            knockback    = self._light_knockback,
            stamina_cost = self._light_stamina,
            element      = self._element,
            hb_offset_x  = self._hb_offset_x,
            hb_offset_y  = self._hb_offset_y,
            hb_width     = self._hb_w_light,
            hb_height    = self._hb_h_light,
            active_frames= self._active_f_light,
            bleed_stack  = self._bleed_stack_light,
            poison_stack = self._poison_stack_light,
        )
        return self._post_process(data, is_heavy=False)

    def get_heavy_attack(self) -> AttackData:
        """返回重攻击参数。重攻击韧性伤害约为轻攻击×3~4倍。"""
        data = AttackData(
            damage       = self._base_heavy_dmg,
            poise_damage = 15.0,   # 重攻击：需2次破韧步兵，约3次破不死族
            knockback    = self._heavy_knockback,
            stamina_cost = self._heavy_stamina,
            element      = self._element,
            hb_offset_x  = self._hb_offset_x,
            hb_offset_y  = self._hb_offset_y,
            hb_width     = self._hb_w_heavy,
            hb_height    = self._hb_h_heavy,
            active_frames= self._active_f_heavy,
            bleed_stack  = self._bleed_stack_light * 2,
            poison_stack = self._poison_stack_light * 2,
        )
        return self._post_process(data, is_heavy=True)

    # ----------------------------------------------------------------
    # 后处理：应用强化 + 词条
    # ----------------------------------------------------------------

    def _post_process(self, data: AttackData, is_heavy: bool = False) -> AttackData:
        # 1. 强化数值（基础伤害 / 韧性伤害 / 流血积累 / 元素覆盖 / 附加伤害）
        if self._upgrade_dmg_mult != 1.0:
            data.damage = max(1, int(data.damage * self._upgrade_dmg_mult))
        if self._upgrade_poise_mult != 1.0:
            data.poise_damage = data.poise_damage * self._upgrade_poise_mult
        if self._upgrade_bleed_mult != 1.0 and data.bleed_stack > 0:
            data.bleed_stack = data.bleed_stack * self._upgrade_bleed_mult
        if self._upgrade_bonus_dmg:
            data.damage += int(self._upgrade_bonus_dmg)
        if self._upgrade_elem_override:
            # 仅在原始元素是物理时覆盖（避免覆盖天然属性武器如圣典）
            if data.element in ("physical", "none"):
                data.element = self._upgrade_elem_override

        # 2. 词条修饰（按列表顺序依次执行）
        for affix in self.affixes:
            try:
                data = affix.modify_attack(data, is_heavy=is_heavy) or data
            except Exception:
                continue
        return data

    # ----------------------------------------------------------------
    # 战技
    # ----------------------------------------------------------------

    def get_weapon_art(self) -> Optional["WeaponArt"]:
        """
        返回当前武器的战技对象（可能为 None，表示无战技）。
        默认返回构造时挂载的 self.weapon_art_obj。
        """
        return self.weapon_art_obj

    # ---- 元数据 ----

    @property
    def element(self) -> str:
        # 元素优先级：强化覆盖 > 类元素
        if self._upgrade_elem_override and self._element in ("physical", "none"):
            return self._upgrade_elem_override
        return self._element

    def __repr__(self) -> str:
        plus = f"+{self.upgrade_level}" if self.upgrade_level > 0 else ""
        return (f"<{self.__class__.__name__}{plus} "
                f"type={self.weapon_type} "
                f"light={self._base_light_dmg} "
                f"heavy={self._base_heavy_dmg} "
                f"elem={self._element} "
                f"affixes={len(self.affixes)}>")
