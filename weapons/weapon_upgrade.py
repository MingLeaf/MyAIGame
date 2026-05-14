# =============================================================
# weapons/weapon_upgrade.py —— 武器强化系统
#
# 功能：
#   - 武器从 +0 强化到 +10
#   - 4 种强化路线（route）：
#       sharp     —— 锋锐：每级 +8% 伤害 + 流血积累 +10%
#       heavy     —— 沉重：每级 +13% 伤害 + 韧性 +5%
#       blessed   —— 加护：每级 +9% 伤害 + 转为 holy 元素
#       elemental —— 元素：每级 +7% 伤害 + 每级 +2 元素附加伤害（默认 fire）
#       none      —— 普通：每级 +10% 伤害（默认路线）
#
#   - 计算结果通过 BaseWeapon.apply_upgrade(...) 写入武器。
#   - 强化曲线 / 路线参数由 data/weapons/upgrade_curve.json 加载，
#     缺失字段自动回退到内置默认。
#
# 使用：
#     from weapons.weapon_upgrade import WeaponUpgrade
#     upgrader = WeaponUpgrade()                        # 加载 JSON
#     upgrader.upgrade_to(weapon, 5, route="sharp")     # 一次性升到 +5 / 锋锐
#     upgrader.preview(level=10, route="heavy")         # 不写入，只返回参数
# =============================================================
from __future__ import annotations

from typing import Optional, Dict, Any
import logging

from utils.json_loader import load_from_data_dir

logger = logging.getLogger(__name__)


# 路线名常量
class UpgradeRoute:
    NONE      = "none"
    SHARP     = "sharp"
    HEAVY     = "heavy"
    BLESSED   = "blessed"
    ELEMENTAL = "elemental"


# 内置默认路线参数（JSON 缺失时兜底）
_DEFAULT_ROUTES: Dict[str, Dict[str, Any]] = {
    UpgradeRoute.NONE: {
        "damage_mult_per_level": 0.10,
        "poise_mult_per_level":  0.00,
        "bleed_mult_per_level":  0.00,
        "element":               None,
        "element_dmg_per_level": 0,
    },
    UpgradeRoute.SHARP: {
        "damage_mult_per_level": 0.08,
        "poise_mult_per_level":  0.00,
        "bleed_mult_per_level":  0.10,
        "element":               None,
        "element_dmg_per_level": 0,
    },
    UpgradeRoute.HEAVY: {
        "damage_mult_per_level": 0.13,
        "poise_mult_per_level":  0.05,
        "bleed_mult_per_level":  0.00,
        "element":               None,
        "element_dmg_per_level": 0,
    },
    UpgradeRoute.BLESSED: {
        "damage_mult_per_level": 0.09,
        "poise_mult_per_level":  0.02,
        "bleed_mult_per_level":  0.00,
        "element":               "holy",
        "element_dmg_per_level": 1,
    },
    UpgradeRoute.ELEMENTAL: {
        "damage_mult_per_level": 0.07,
        "poise_mult_per_level":  0.00,
        "bleed_mult_per_level":  0.00,
        "element":               "fire",
        "element_dmg_per_level": 2,
    },
}

_DEFAULT_MAX_LEVEL = 10


class WeaponUpgrade:
    """
    武器强化器（无状态实例，仅负责数值计算与写入）。
    """

    def __init__(self, *, json_path: str = "weapons/upgrade_curve.json"):
        self.max_level: int = _DEFAULT_MAX_LEVEL
        self.routes:    Dict[str, Dict[str, Any]] = {
            k: dict(v) for k, v in _DEFAULT_ROUTES.items()
        }
        self._json_path = json_path
        self._load_json()

    # ----------------------------------------------------------------
    # JSON 加载
    # ----------------------------------------------------------------

    def _load_json(self) -> None:
        try:
            cfg = load_from_data_dir(self._json_path)
        except FileNotFoundError:
            logger.warning("WeaponUpgrade: 未找到 '%s'，使用内置默认值",
                           self._json_path)
            return
        except Exception as exc:
            logger.exception("WeaponUpgrade: 加载 '%s' 失败：%s",
                             self._json_path, exc)
            return

        self.max_level = int(cfg.get("max_level", _DEFAULT_MAX_LEVEL))
        routes_cfg = cfg.get("routes", {})
        for name, params in routes_cfg.items():
            base = self.routes.get(name, dict(_DEFAULT_ROUTES[UpgradeRoute.NONE]))
            base.update(params or {})
            self.routes[name] = base

    # ----------------------------------------------------------------
    # 数值计算
    # ----------------------------------------------------------------

    def calculate_params(self, level: int, route: str = UpgradeRoute.NONE) -> dict:
        """
        计算指定路线 + 等级下的强化参数（不会修改武器）。
        :return: dict(dmg_mult, poise_mult, bleed_mult, elem_override, bonus_dmg)
        """
        level = max(0, min(int(level), self.max_level))
        cfg   = self.routes.get(route, self.routes[UpgradeRoute.NONE])
        return {
            "level":         level,
            "route":         route,
            "dmg_mult":      1.0 + cfg.get("damage_mult_per_level", 0.10) * level,
            "poise_mult":    1.0 + cfg.get("poise_mult_per_level",  0.00) * level,
            "bleed_mult":    1.0 + cfg.get("bleed_mult_per_level",  0.00) * level,
            "elem_override": cfg.get("element") if level > 0 else None,
            "bonus_dmg":     int(cfg.get("element_dmg_per_level", 0) * level),
        }

    # 别名
    preview = calculate_params

    # ----------------------------------------------------------------
    # 写入武器
    # ----------------------------------------------------------------

    def upgrade_to(self, weapon, level: int, route: str = UpgradeRoute.NONE) -> dict:
        """
        将 weapon 一次性强化到指定等级 + 路线。
        :return: 计算结果 dict（同 calculate_params 返回值）
        """
        params = self.calculate_params(level, route)
        weapon.apply_upgrade(
            level         = params["level"],
            route         = params["route"],
            dmg_mult      = params["dmg_mult"],
            poise_mult    = params["poise_mult"],
            bleed_mult    = params["bleed_mult"],
            elem_override = params["elem_override"],
            bonus_dmg     = params["bonus_dmg"],
        )
        # 派发事件
        try:
            from core.event_manager import event_manager
            event_manager.emit("weapon_upgraded", {
                "weapon": weapon,
                "level":  params["level"],
                "route":  params["route"],
            })
        except Exception:
            pass
        return params

    def upgrade_one(self, weapon, route: Optional[str] = None) -> Optional[dict]:
        """
        将武器从当前等级 +1。返回 None 表示已满级。
        若指定 route，则同时切换路线（重置后从 0 开始升 N 级）。
        """
        current_level = getattr(weapon, "upgrade_level", 0)
        current_route = getattr(weapon, "upgrade_route", UpgradeRoute.NONE)
        next_route    = route or current_route or UpgradeRoute.NONE
        next_level    = current_level + 1
        if next_level > self.max_level:
            return None
        return self.upgrade_to(weapon, next_level, next_route)

    # ----------------------------------------------------------------
    # 调试/查询
    # ----------------------------------------------------------------

    def list_routes(self) -> list[str]:
        return list(self.routes.keys())


# 全局便捷实例（按需获取）
_default_upgrader: Optional[WeaponUpgrade] = None


def get_default_upgrader() -> WeaponUpgrade:
    global _default_upgrader
    if _default_upgrader is None:
        _default_upgrader = WeaponUpgrade()
    return _default_upgrader


__all__ = [
    "WeaponUpgrade", "UpgradeRoute",
    "get_default_upgrader",
]
