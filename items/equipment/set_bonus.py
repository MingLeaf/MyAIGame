# =============================================================
# items/equipment/set_bonus.py —— 套装效果计算
#
# 设计：
#   - 每件 ArmorItem 可挂载 set_id 字段（在 data/items/armors.json
#     的 "set_id" 配置）。
#   - SetBonusManager 挂载在 player 上，订阅 "equipment_changed"
#     事件，每次装备变化重新计算激活的套装。
#   - 套装阈值（threshold）满足时：
#       1. 派发 "set_bonus_activated" 事件
#       2. 根据 bonus dict 修改玩家衍生属性（poise/def_bonus/...）
#       3. UI 层（FloatingText）订阅事件后显示飘字
#   - 套装解除时派发 "set_bonus_deactivated" 事件并回滚修改。
#
# 当前阶段加成实现：
#   - poise           : 直接累加到 growth.bonus_poise（暂存属性）
#   - mana_max        : 直接累加到 stats.max_mana
#   - 其他类型仅派发事件供后续系统监听（不破坏数值）
# =============================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player


@dataclass
class SetBonus:
    """单个套装效果定义。"""
    set_id:      str
    set_name:    str
    threshold:   int
    bonus:       Dict[str, float] = field(default_factory=dict)
    description: str = ""


class SetBonusManager:
    """
    套装效果管理器。

    挂载方式（在 Player.__init__ 中）：
        self.set_bonus = SetBonusManager(self)

    每次装备变化由 Equipment.equip / unequip 派发的
    "equipment_changed" 事件触发 update()，
    或外部直接调用 update() 强制刷新。
    """

    def __init__(self, player: "Player"):
        self._player = player
        self._registry:  Dict[str, SetBonus] = {}
        self._active:    Dict[str, SetBonus] = {}    # 当前激活的套装
        # 已应用到 stats/growth 的修改记录，用于解除时回滚
        self._applied_mods: Dict[str, Dict[str, float]] = {}

        # 订阅装备变化（在 player 销毁时由场景解订阅）
        event_manager.subscribe("equipment_changed", self._on_equipment_changed)

    # ----------------------------------------------------------------
    # 注册接口
    # ----------------------------------------------------------------

    def register(self, bonus: SetBonus) -> None:
        """注册一个套装效果。重复注册会覆盖。"""
        self._registry[bonus.set_id] = bonus

    def register_many(self, bonuses: List[SetBonus]) -> None:
        for b in bonuses:
            self.register(b)

    def list_registered(self) -> List[str]:
        return list(self._registry.keys())

    def is_active(self, set_id: str) -> bool:
        return set_id in self._active

    def active_set_ids(self) -> List[str]:
        return list(self._active.keys())

    # ----------------------------------------------------------------
    # 计算 / 更新
    # ----------------------------------------------------------------

    def _on_equipment_changed(self, _data: dict) -> None:
        # 装备改动 → 重新计算
        try:
            self.update()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception(
                "SetBonusManager.update 异常: %s", exc)

    def update(self) -> None:
        """重新统计已装备护甲，激活/解除套装效果。"""
        equipment = getattr(self._player, "equipment", None)
        if equipment is None:
            return

        # 收集已装备的 set_id 计数
        # 4 件护甲槽（与 player/equipment.py 中常量保持一致）
        slots = ("head", "chest", "hands", "legs")
        counts: Dict[str, int] = {}
        for slot in slots:
            item = equipment.get(slot)
            if item is None:
                continue
            sid = getattr(item, "set_id", "") or ""
            if not sid:
                continue
            counts[sid] = counts.get(sid, 0) + 1

        # 决定新激活集合
        new_active: Dict[str, SetBonus] = {}
        for set_id, cnt in counts.items():
            bonus = self._registry.get(set_id)
            if bonus and cnt >= bonus.threshold:
                new_active[set_id] = bonus

        # 处理变化
        for set_id, bonus in new_active.items():
            if set_id not in self._active:
                self._activate(set_id, bonus)
        for set_id, bonus in list(self._active.items()):
            if set_id not in new_active:
                self._deactivate(set_id, bonus)

        self._active = new_active

    # ----------------------------------------------------------------
    # 应用 / 回滚
    # ----------------------------------------------------------------

    def _activate(self, set_id: str, bonus: SetBonus) -> None:
        applied = self._apply_bonus(bonus)
        self._applied_mods[set_id] = applied
        event_manager.emit("set_bonus_activated", {
            "set_id":   set_id,
            "set_name": bonus.set_name,
            "bonus":    dict(bonus.bonus),
            "player":   self._player,
        })

    def _deactivate(self, set_id: str, bonus: SetBonus) -> None:
        applied = self._applied_mods.pop(set_id, {})
        self._revert_bonus(applied)
        event_manager.emit("set_bonus_deactivated", {
            "set_id":   set_id,
            "set_name": bonus.set_name,
            "player":   self._player,
        })

    def _apply_bonus(self, bonus: SetBonus) -> Dict[str, float]:
        """
        应用套装数值加成到玩家。
        返回实际写入的字段 → 数值（用于回滚）。
        """
        player = self._player
        applied: Dict[str, float] = {}

        for k, v in bonus.bonus.items():
            v = float(v)
            stats  = getattr(player, "stats",  None)
            growth = getattr(player, "growth", None)

            if k == "mana_max" and stats is not None:
                stats.max_mana = int(stats.max_mana + v)
                stats.mana = min(stats.mana + int(v), stats.max_mana)
                applied[k] = v

            elif k == "poise" and growth is not None:
                cur = getattr(growth, "bonus_poise", 0.0)
                setattr(growth, "bonus_poise", cur + v)
                applied[k] = v

            elif k == "stamina_regen" and stats is not None:
                stats.STAMINA_REGEN = float(stats.STAMINA_REGEN) + v  # type: ignore[attr-defined]
                applied[k] = v

            # ---- 第 7 阶段补丁：让以下套装效果真正生效 ----
            elif k == "def_bonus" and stats is not None:
                # 物理减伤百分比累加（10% → 0.10）
                stats.def_bonus_pct = float(stats.def_bonus_pct) + v
                applied[k] = v

            elif k == "atk_bonus" and stats is not None:
                # 攻击力百分比加成（HitResolver 读取使用）
                stats.atk_bonus_pct = float(stats.atk_bonus_pct) + v
                applied[k] = v

            elif k == "magic_dmg" and stats is not None:
                # 魔法伤害百分比加成
                stats.magic_bonus_pct = float(stats.magic_bonus_pct) + v
                applied[k] = v

            elif k == "roll_iframes" and growth is not None:
                cur = getattr(growth, "roll_iframes_bonus", 0.0)
                setattr(growth, "roll_iframes_bonus", cur + v)
                applied[k] = v

            else:
                # 未知字段：仅记录数值供事件层使用，不触碰玩家状态
                applied[k] = v
        return applied

    def _revert_bonus(self, applied: Dict[str, float]) -> None:
        player = self._player
        for k, v in applied.items():
            v = float(v)
            stats  = getattr(player, "stats",  None)
            growth = getattr(player, "growth", None)

            if k == "mana_max" and stats is not None:
                stats.max_mana = max(0, int(stats.max_mana - v))
                stats.mana = min(stats.mana, stats.max_mana)
            elif k == "poise" and growth is not None:
                cur = getattr(growth, "bonus_poise", 0.0)
                setattr(growth, "bonus_poise", max(0.0, cur - v))
            elif k == "stamina_regen" and stats is not None:
                stats.STAMINA_REGEN = float(stats.STAMINA_REGEN) - v  # type: ignore[attr-defined]
            elif k == "def_bonus" and stats is not None:
                stats.def_bonus_pct = max(0.0, float(stats.def_bonus_pct) - v)
            elif k == "atk_bonus" and stats is not None:
                stats.atk_bonus_pct = max(0.0, float(stats.atk_bonus_pct) - v)
            elif k == "magic_dmg" and stats is not None:
                stats.magic_bonus_pct = max(0.0, float(stats.magic_bonus_pct) - v)
            elif k == "roll_iframes" and growth is not None:
                cur = getattr(growth, "roll_iframes_bonus", 0.0)
                setattr(growth, "roll_iframes_bonus", max(0.0, cur - v))
            # 其它仅事件，无需回滚

    # ----------------------------------------------------------------
    # 析构 / 取消订阅
    # ----------------------------------------------------------------

    def dispose(self) -> None:
        try:
            event_manager.unsubscribe("equipment_changed", self._on_equipment_changed)
        except Exception:
            pass
        # 解除全部已激活
        for set_id, bonus in list(self._active.items()):
            self._deactivate(set_id, bonus)
        self._active.clear()


__all__ = ["SetBonus", "SetBonusManager"]
