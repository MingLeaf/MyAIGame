# =============================================================
# combat/status_effect_manager.py —— 状态异常管理器（兼容别名）
#
# 第 4 阶段重构：实际实现位于 combat/status_manager.py
# 此处仅做导入聚合，对应开发文档中的命名 status_effect_manager.py
# =============================================================
from __future__ import annotations

from combat.status_manager import StatusManager

__all__ = ["StatusManager"]
