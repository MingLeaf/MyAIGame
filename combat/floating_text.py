# =============================================================
# combat/floating_text.py —— 伤害飘字（兼容包装）
#
# 本模块现已迁移至 ui/damage_number.py，此处保留为兼容导入。
# 所有 from combat.floating_text import ... 继续生效，
# 实际符号均来自 ui.damage_number。
# =============================================================

from ui.damage_number import (
    FloatingText,
    FloatingTextManager,
    DAMAGE_TYPE_COLORS,
    _DEFAULT_LIFETIME,
    _DEFAULT_RISE_PX,
    _DEFAULT_FONT_SIZE,
    _pick_font_size,
)

# 向后兼容：保留旧常量名
_CRIT_COLOR  = DAMAGE_TYPE_COLORS["crit"]
_HEAL_COLOR  = DAMAGE_TYPE_COLORS["heal"]
_DEFAULT_COLOR = DAMAGE_TYPE_COLORS["default"]
_SIZE_THRESHOLDS = [
    (50, 24),
    (20, 20),
    (0,  16),
]
