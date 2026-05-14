# =============================================================
# entities/player/player_stats.py —— 玩家数值系统
#
# 负责：HP / Stamina / Mana 的运行时管理。
# 上限由 GrowthStats 的衍生值动态写入（由 Player 在升级/装备变化时调用
# apply_growth() 统一同步）。
# =============================================================
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.player.growth_stats import GrowthStats


class PlayerStats:
    """
    玩家基础数值：HP / Stamina / Mana。
    提供增减、恢复、死亡判断等接口。
    上限通过 apply_growth(growth) 从成长属性同步。
    """

    # ---- 基准值（角色初始，不含成长加成）----
    BASE_HP       = 100
    BASE_STAMINA  = 100
    BASE_MANA     = 50
    BASE_ATK      = 0      # 角色攻击力加成基值（由 GrowthStats.get_atk_bonus() 覆盖）

    # 每秒自动恢复量
    STAMINA_REGEN  = 30.0   # 点/秒（体魄成长可在此基础上提升）
    STAMINA_DELAY  = 1.2    # 停止消耗后延迟多少秒才开始恢复

    def __init__(self):
        self.max_hp:      int   = self.BASE_HP
        self.hp:          int   = self.BASE_HP
        self.max_stamina: float = float(self.BASE_STAMINA)
        self.stamina:     float = float(self.BASE_STAMINA)
        self.max_mana:    int   = self.BASE_MANA
        self.mana:        int   = self.BASE_MANA
        self.atk:         int   = self.BASE_ATK   # 叠加到武器 base_damage 参与伤害计算

        # ---- 第 7 阶段补丁：装备防御 + 武器额外攻击 + 套装百分比加成 ----
        # 由 Equipment._sync_stats 在每次装备/卸下后写入
        self.armor_defense:     int   = 0     # 4 件护甲防御之和
        self.weapon_item_atk:   int   = 0     # 当前武器物品的 base_atk
        # 套装效果（百分比，0.0 = 无加成；由 SetBonusManager 累加/回滚）
        self.atk_bonus_pct:     float = 0.0   # 物理 / 武器伤害百分比加成
        self.def_bonus_pct:     float = 0.0   # 物理减伤百分比（最终在防御计算后再乘 (1 - pct)）
        self.magic_bonus_pct:   float = 0.0   # 魔法伤害百分比加成
        self.magic_res_bonus:   int   = 0     # 魔法抗性数值加成（来自魔法长袍等）

        self._stamina_regen_timer: float = 0.0
        self._stamina_consumed:    bool  = False

    # ----------------------------------------------------------------
    # 成长属性同步（升级或装备变化后调用）
    # ----------------------------------------------------------------

    def apply_growth(self, growth: "GrowthStats",
                     weapon=None) -> None:
        """
        将 GrowthStats 的衍生值同步到本对象。
        应在以下时机调用：
          - 分配属性点后
          - 装备/卸下武器后
          - 场景加载完成后
        """
        # 最大HP = 基准 + 体魄加成
        new_max_hp = self.BASE_HP + growth.max_hp_bonus
        if new_max_hp != self.max_hp:
            delta = new_max_hp - self.max_hp
            self.max_hp = new_max_hp
            # 同步当前HP（上限提升时等比例提升，下限时裁剪）
            self.hp = min(self.hp + max(0, delta), self.max_hp)

        # 最大耐力 = 基准 + 耐性加成
        new_max_sta = self.BASE_STAMINA + growth.max_stamina_bonus
        if new_max_sta != self.max_stamina:
            self.max_stamina = new_max_sta
            self.stamina = min(self.stamina, self.max_stamina)

        # 角色物理攻击力加成
        self.atk = growth.get_atk_bonus(weapon)

    # ----------------------------------------------------------------
    # 每帧更新
    # ----------------------------------------------------------------

    def update(self, dt: float):
        """每帧自动恢复耐力。"""
        if self._stamina_consumed:
            self._stamina_regen_timer = self.STAMINA_DELAY
            self._stamina_consumed = False
        else:
            if self._stamina_regen_timer > 0:
                self._stamina_regen_timer -= dt
            else:
                self.stamina = min(self.max_stamina,
                                   self.stamina + self.STAMINA_REGEN * dt)

    # ----------------------------------------------------------------
    # HP
    # ----------------------------------------------------------------

    def take_damage(self, amount: int) -> int:
        """
        受到伤害（不带防御计算的旧接口）。
        子系统应优先通过 PlayerCombat.take_damage 走完整伤害流程。
        """
        actual = min(amount, self.hp)
        self.hp -= actual
        return actual

    def take_damage_with_defense(self, raw_damage: int,
                                 element: str = "physical") -> tuple[int, int]:
        """
        带护甲减伤的受击入口（第 7 阶段补丁）。
        :param raw_damage: 攻击者原始伤害
        :param element:    攻击元素（physical / magic / fire / ice ...）
        :return: (final_damage, actual_consumed_hp)

        计算公式：
            after_armor   = raw_damage - armor_defense * DEFENSE_COEFF
                           （魔法系攻击改为 - magic_res_bonus * 0.5）
            after_set     = after_armor * (1 - def_bonus_pct)
            final         = max(MIN_DAMAGE, after_set)
        """
        from combat.damage_calculator import (
            _DEFENSE_COEFF, _MIN_DAMAGE,
        )

        # 1. 数值防御（物理 → armor_defense；魔法 → magic_res_bonus）
        if element in ("magic", "fire", "ice", "lightning", "dark", "arcane", "holy"):
            defense_value = float(self.magic_res_bonus)
        else:
            defense_value = float(self.armor_defense)

        after_armor = float(raw_damage) - defense_value * _DEFENSE_COEFF

        # 2. 套装百分比减伤
        after_set = after_armor * max(0.0, 1.0 - self.def_bonus_pct)

        # 3. 下限保护
        final = max(_MIN_DAMAGE, int(after_set))

        # 4. 扣 HP
        actual = min(final, self.hp)
        self.hp -= actual
        return final, actual

    def heal(self, amount: int) -> int:
        """治疗，返回实际回复量。"""
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    # ----------------------------------------------------------------
    # Stamina
    # ----------------------------------------------------------------

    def consume_stamina(self, amount: float) -> bool:
        if self.stamina < amount:
            return False
        self.stamina -= amount
        self._stamina_consumed = True
        return True

    def try_consume_stamina(self, amount: float) -> bool:
        return self.consume_stamina(amount)

    @property
    def stamina_ratio(self) -> float:
        return self.stamina / self.max_stamina if self.max_stamina > 0 else 0.0

    @property
    def stamina_empty(self) -> bool:
        return self.stamina <= 0

    # ----------------------------------------------------------------
    # Mana
    # ----------------------------------------------------------------

    def consume_mana(self, amount: int) -> bool:
        if self.mana < amount:
            return False
        self.mana -= amount
        return True

    def restore_mana(self, amount: int):
        self.mana = min(self.max_mana, self.mana + amount)

    @property
    def mana_ratio(self) -> float:
        return self.mana / self.max_mana if self.max_mana > 0 else 0.0
