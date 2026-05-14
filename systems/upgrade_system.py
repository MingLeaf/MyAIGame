# =============================================================
# systems/upgrade_system.py —— 武器强化系统
#
# 第 8 阶段：在营地/铁匠处消耗材料 + 灵魂碎片强化武器。
# 包装已有 weapons/weapon_upgrade.py 的数值计算能力，
# 增加成本校验与材料扣除逻辑。
#
# 规则：
#   - +1~+5：仅消耗灵魂碎片
#   - +6~+10：消耗灵魂碎片 + 路线专属材料
#   - +5 后选择强化路线（sharp / heavy / blessed / elemental）
#
# 成本配置：data/balance/upgrade_cost.json
# 强化曲线：data/weapons/upgrade_curve.json
#
# 使用：
#   from systems.upgrade_system import UpgradeSystem
#   ok, msg = UpgradeSystem.upgrade_weapon(player, weapon, route="sharp")
# =============================================================
from __future__ import annotations
from typing import Optional, Tuple, TYPE_CHECKING
import logging

from core.event_manager import event_manager

if TYPE_CHECKING:
    from entities.player.player import Player
    from weapons.base_weapon import BaseWeapon

logger = logging.getLogger(__name__)


class UpgradeSystem:
    """
    武器强化管理器（全静态方法）。
    """

    _cost_data: Optional[list] = None
    _materials_cfg: Optional[dict] = None
    _route_branch_level: int = 5
    _loaded: bool = False

    # ----------------------------------------------------------------
    # 数据加载
    # ----------------------------------------------------------------

    @classmethod
    def load_data(cls) -> None:
        if cls._loaded:
            return
        cls._loaded = True

        try:
            from utils.json_loader import load_from_data_dir
            cfg = load_from_data_dir("balance/upgrade_cost.json")
            cls._cost_data = cfg.get("levels", [])
            cls._materials_cfg = cfg.get("materials", {})
            cls._route_branch_level = cfg.get("route_branch_level", 5)
        except Exception:
            logger.warning("UpgradeSystem: 无法加载 upgrade_cost.json")
            cls._cost_data = []
            cls._materials_cfg = {}
            cls._route_branch_level = 5

    # ----------------------------------------------------------------
    # 成本查询
    # ----------------------------------------------------------------

    @classmethod
    def get_upgrade_cost(cls, next_level: int) -> Tuple[int, int, str]:
        """
        查询升到指定等级的成本。
        :param next_level: 目标等级 (1~10)
        :return: (souls_cost, material_qty, material_item_id)
        """
        cls.load_data()
        if not cls._cost_data or next_level < 1 or next_level > 10:
            return (0, 0, "")

        # 索引从 0 开始（level-1）
        idx = next_level - 1
        if idx >= len(cls._cost_data):
            return (0, 0, "")

        entry = cls._cost_data[idx]
        souls = entry.get("souls", 0)
        mat_qty = entry.get("material_qty", 0)
        return (souls, mat_qty, "")

    @classmethod
    def get_material_for_route(cls, route: str) -> dict:
        """获取路线对应的材料信息。"""
        cls.load_data()
        return cls._materials_cfg.get(route, {})

    # ----------------------------------------------------------------
    # 强化操作
    # ----------------------------------------------------------------

    @classmethod
    def upgrade_weapon(cls, player: "Player",
                       weapon: Optional["BaseWeapon"] = None,
                       route: str = "none") -> Tuple[bool, str]:
        """
        将武器强化一级。

        :param player: 玩家实例（需要 soul_fragments + 背包检查）
        :param weapon: 要强化的武器（默认取 player.weapon）
        :param route:  强化路线（仅 +5 时选择分路线，否则沿用当前路线）
        :return: (success: bool, message: str)
        """
        cls.load_data()

        if player is None:
            return False, "玩家不存在"

        if weapon is None:
            weapon = getattr(player, "weapon", None)
        if weapon is None:
            return False, "没有可强化的武器"

        # 当前等级
        current_level = getattr(weapon, "upgrade_level", 0)
        current_route = getattr(weapon, "upgrade_route", "none")
        next_level = current_level + 1

        # 检查满级
        if next_level > 10:
            return False, "武器已达最大强化等级（+10）"

        # 路线分支检查：+5 时必须选择路线
        if next_level > cls._route_branch_level:
            if route == "none":
                return False, f"+{cls._route_branch_level}以后必须指定强化路线"
            if current_route != route and current_level >= cls._route_branch_level:
                # 升级到 +6 时首次选择路线
                pass

        # 确定使用的路线（首次进入分支时使用新路线）
        effective_route = route if next_level > cls._route_branch_level else current_route

        # ---- 检查成本 ----
        souls_cost, mat_qty, _ = cls.get_upgrade_cost(next_level)

        # 灵魂碎片检查
        soul_fragments = getattr(player, "soul_fragments", 0)
        if soul_fragments < souls_cost:
            return False, f"灵魂碎片不足（需要 {souls_cost}，当前 {soul_fragments}）"

        # 材料检查（+6 起步需要材料）
        if mat_qty > 0:
            mat_info = cls._materials_cfg.get(effective_route, {})
            mat_item_id = mat_info.get("item_id", "")
            mat_name = mat_info.get("name", effective_route)

            if mat_item_id:
                inv = getattr(player, "inventory", None)
                if inv is not None:
                    have_qty = inv.count(mat_item_id)
                    if have_qty < mat_qty:
                        return False, f"{mat_name}不足（需要 {mat_qty}，当前 {have_qty}）"

        # ---- 执行强化 ----
        # 扣除灵魂碎片
        player.soul_fragments = soul_fragments - souls_cost

        # 扣除材料
        if mat_qty > 0:
            mat_info = cls._materials_cfg.get(effective_route, {})
            mat_item_id = mat_info.get("item_id", "")
            if mat_item_id:
                inv = getattr(player, "inventory", None)
                if inv is not None:
                    inv.remove_item_id(mat_item_id, mat_qty)

        # 调用底层强化器
        from weapons.weapon_upgrade import WeaponUpgrade
        upgrader = WeaponUpgrade()
        params = upgrader.upgrade_to(weapon, next_level, effective_route)

        # 同步玩家属性（武器攻击力变化）—— 走完整装备同步路径
        equipment = getattr(player, "equipment", None)
        if equipment is not None:
            equipment._sync_stats()
        else:
            player.stats.apply_growth(player.growth, player.weapon)

        # 事件广播
        event_manager.emit("soul_fragments_changed", {
            "amount": -souls_cost,
            "total":  player.soul_fragments,
            "source": "weapon_upgrade",
        })
        event_manager.emit("weapon_upgraded", {
            "weapon": weapon,
            "level":  next_level,
            "route":  effective_route,
            "cost":   souls_cost,
        })

        route_name = effective_route if effective_route != "none" else ""
        return True, f"+{next_level} {route_name} 强化成功"

    # ----------------------------------------------------------------
    # 预览接口
    # ----------------------------------------------------------------

    @classmethod
    def preview_upgrade(cls, player: "Player",
                        weapon: Optional["BaseWeapon"] = None) -> dict:
        """
        预览下一次强化的信息和成本，不实际执行。

        :return: dict{
            current_level, next_level, souls_cost, mat_qty, mat_item_id,
            can_afford_souls, can_afford_materials
        }
        """
        cls.load_data()
        if player is None:
            return {"error": "玩家不存在"}

        if weapon is None:
            weapon = getattr(player, "weapon", None)
        if weapon is None:
            return {"error": "没有武器"}

        current_level = getattr(weapon, "upgrade_level", 0)
        next_level = current_level + 1

        if next_level > 10:
            return {"error": "已满级", "current_level": current_level}

        souls_cost, mat_qty, _ = cls.get_upgrade_cost(next_level)
        soul_fragments = getattr(player, "soul_fragments", 0)

        result = {
            "current_level":      current_level,
            "next_level":         next_level,
            "souls_cost":         souls_cost,
            "mat_qty":            mat_qty,
            "can_afford_souls":   soul_fragments >= souls_cost,
            "needs_route":        next_level > cls._route_branch_level,
        }

        if mat_qty > 0:
            current_route = getattr(weapon, "upgrade_route", "none")
            mat_info = cls._materials_cfg.get(current_route, {})
            result["mat_item_id"] = mat_info.get("item_id", "")
            result["mat_name"] = mat_info.get("name", "")

            inv = getattr(player, "inventory", None)
            have = inv.count(result["mat_item_id"]) if inv else 0
            result["mat_have"] = have
            result["can_afford_materials"] = have >= mat_qty

        return result


__all__ = ["UpgradeSystem"]
