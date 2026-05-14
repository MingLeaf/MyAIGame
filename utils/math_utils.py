# =============================================================
# utils/math_utils.py —— 数学工具函数
# =============================================================

import math


# -------------------------------------------------------
# 二维向量工具
# -------------------------------------------------------

def vec_add(a, b):
    """向量加法"""
    return (a[0] + b[0], a[1] + b[1])


def vec_sub(a, b):
    """向量减法"""
    return (a[0] - b[0], a[1] - b[1])


def vec_scale(v, s):
    """向量缩放"""
    return (v[0] * s, v[1] * s)


def vec_dot(a, b):
    """点积"""
    return a[0] * b[0] + a[1] * b[1]


def vec_length(v):
    """向量长度"""
    return math.sqrt(v[0] ** 2 + v[1] ** 2)


def vec_normalize(v):
    """归一化向量，零向量返回 (0, 0)"""
    length = vec_length(v)
    if length == 0:
        return (0.0, 0.0)
    return (v[0] / length, v[1] / length)


def vec_distance(a, b):
    """两点距离"""
    return vec_length(vec_sub(b, a))


def vec_lerp(a, b, t):
    """线性插值，t 在 [0, 1]"""
    t = clamp(t, 0.0, 1.0)
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t)


def vec_angle(v):
    """向量与 X 轴的夹角（弧度）"""
    return math.atan2(v[1], v[0])


def vec_from_angle(angle, length=1.0):
    """从角度生成向量"""
    return (math.cos(angle) * length, math.sin(angle) * length)


# -------------------------------------------------------
# 标量工具
# -------------------------------------------------------

def clamp(value, min_val, max_val):
    """限制 value 在 [min_val, max_val] 范围内"""
    return max(min_val, min(max_val, value))


def lerp(a, b, t):
    """标量线性插值"""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def sign(value):
    """返回符号：-1 / 0 / 1"""
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def approach(current, target, step):
    """以 step 的步长向 target 逼近 current，不超过 target"""
    if current < target:
        return min(current + step, target)
    if current > target:
        return max(current - step, target)
    return target


def deg_to_rad(deg):
    return math.radians(deg)


def rad_to_deg(rad):
    return math.degrees(rad)


def angle_diff(a, b):
    """两个弧度角之间的最短差值（有符号，范围 -π ~ π）"""
    diff = (b - a) % (2 * math.pi)
    if diff > math.pi:
        diff -= 2 * math.pi
    return diff
